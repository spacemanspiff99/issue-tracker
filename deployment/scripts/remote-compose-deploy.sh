#!/usr/bin/env bash
set -euo pipefail

target_host="${TARGET_HOST:?TARGET_HOST is required}"
target_user="${TARGET_USER:-akun}"
deploy_environment="${DEPLOY_ENVIRONMENT:-}"
app_environment="${APP_ENVIRONMENT:-}"
expected_target_host="${EXPECTED_TARGET_HOST:-}"
expected_target_hostname="${EXPECTED_TARGET_HOSTNAME:-}"
deploy_path="${DEPLOY_PATH:-/home/akun/issue-tracker}"
compose_file="${COMPOSE_FILE:-deployment/docker-compose.local.yml}"
remote_env_file="${REMOTE_ENV_FILE:-}"
app_base_url="${APP_BASE_URL:-http://${target_host}:8000}"
# Public APP_BASE_URL may be an HTTPS proxy hostname the target host cannot resolve or trust;
# health is checked on the target host directly unless APP_HEALTHCHECK_URL overrides it.
app_healthcheck_url="${APP_HEALTHCHECK_URL:-${app_base_url}/health}"
app_http_port="${APP_HTTP_PORT:-8000}"
# Isolation for co-hosted stacks (UAT on the dev host). Empty keeps compose defaults,
# which is what existing single-purpose hosts (prod) rely on for their volume names.
compose_project_name="${COMPOSE_PROJECT_NAME:-}"
postgres_container_name="${POSTGRES_CONTAINER_NAME:-}"
run_browser_uat="${RUN_BROWSER_UAT:-0}"
skip_db_backup="${SKIP_DB_BACKUP:-0}"
run_tests="${RUN_TESTS:-0}"
run_ruff="${RUN_RUFF:-0}"
expected_deploy_sha="${EXPECTED_DEPLOY_SHA:-}"
# TARGET_MODE=ssh (default) copies to TARGET_HOST over SSH. TARGET_MODE=local deploys onto this
# machine without SSH or GitHub Actions; the source is `git archive` of EXPECTED_DEPLOY_SHA.
target_mode="${TARGET_MODE:-ssh}"
dry_run="${DEPLOY_DRY_RUN:-0}"
remote="${target_user}@${target_host}"
ssh_opts=(-o BatchMode=yes -o ConnectTimeout=15 -o ServerAliveInterval=10 -o ServerAliveCountMax=3)
if [ -n "${DEPLOY_SSH_KEY_PATH:-}" ]; then
  ssh_opts+=(-i "$DEPLOY_SSH_KEY_PATH" -o IdentitiesOnly=yes)
fi
if [ -n "${DEPLOY_KNOWN_HOSTS_PATH:-}" ]; then
  ssh_opts+=(-o "UserKnownHostsFile=$DEPLOY_KNOWN_HOSTS_PATH" -o StrictHostKeyChecking=yes)
fi

if [ -n "$expected_target_host" ] && [ "$target_host" != "$expected_target_host" ]; then
  echo "Refusing $deploy_environment deploy: TARGET_HOST '$target_host' does not match expected '$expected_target_host'" >&2
  exit 2
fi

if [ "$deploy_environment" = "prod" ] && [ -z "$remote_env_file" ]; then
  echo "Refusing prod deploy: REMOTE_ENV_FILE is required so prod does not reuse UAT/default config" >&2
  exit 2
fi

if [ "$deploy_environment" = "prod" ] && [ "$skip_db_backup" = "1" ]; then
  echo "Refusing prod deploy: SKIP_DB_BACKUP=1 is not allowed" >&2
  exit 2
fi

case "$target_mode" in
  ssh) ;;
  local)
    if [ -z "$expected_deploy_sha" ]; then
      echo "Refusing local deploy: EXPECTED_DEPLOY_SHA is required" >&2
      exit 2
    fi
    if ! resolved_sha="$(git rev-parse --verify --quiet "${expected_deploy_sha}^{commit}")" || [ "$resolved_sha" != "$expected_deploy_sha" ]; then
      echo "Refusing local deploy: EXPECTED_DEPLOY_SHA must be a full 40-char commit SHA present locally" >&2
      exit 2
    fi
    if [ -z "$(git branch -r --contains "$expected_deploy_sha" 2>/dev/null)" ]; then
      echo "Refusing local deploy: $expected_deploy_sha is not on any pushed remote branch (run git fetch, push first)" >&2
      exit 2
    fi
    if ! hostname -I 2>/dev/null | tr ' ' '\n' | grep -qx "$target_host"; then
      echo "Refusing local deploy: TARGET_HOST '$target_host' is not an address of this machine" >&2
      exit 2
    fi
    GITHUB_SHA="$expected_deploy_sha"
    GITHUB_REF="local:$(git branch -r --contains "$expected_deploy_sha" | sed 's/^ *//' | paste -sd, -)"
    ;;
  *)
    echo "Refusing deploy: TARGET_MODE must be ssh or local (got '$target_mode')" >&2
    exit 2
    ;;
esac
release_id="${GITHUB_SHA:-manual}-$(date -u +%Y%m%d%H%M%S)"

if [ -n "$expected_deploy_sha" ] && [ "${GITHUB_SHA:-}" != "$expected_deploy_sha" ]; then
  echo "Refusing $deploy_environment deploy: GITHUB_SHA '${GITHUB_SHA:-}' does not match EXPECTED_DEPLOY_SHA '$expected_deploy_sha'" >&2
  exit 2
fi

if [ -z "$app_environment" ]; then
  case "$deploy_environment" in
    prod) app_environment="production" ;;
    uat) app_environment="uat" ;;
    *) app_environment="${deploy_environment:-development}" ;;
  esac
fi

case "$deploy_path" in
  /home/*/issue-tracker|/home/*/issue-tracker-uat|/opt/issue-tracker|/srv/issue-tracker) ;;
  *)
    echo "Refusing unsafe DEPLOY_PATH: $deploy_path" >&2
    exit 2
    ;;
esac

if [ "$deploy_environment" = "uat" ]; then
  # UAT shares a host with the live dev app: it must never reuse the dev compose project,
  # dev checkout, dev postgres container, or dev port.
  case "$compose_project_name" in
    ""|deployment)
      echo "Refusing uat deploy: COMPOSE_PROJECT_NAME must be set to a UAT-only name (got '${compose_project_name}')" >&2
      exit 2
      ;;
  esac
  if [ -z "$postgres_container_name" ] || [ "$postgres_container_name" = "issue-tracker-postgres" ]; then
    echo "Refusing uat deploy: POSTGRES_CONTAINER_NAME must be set to a UAT-only name" >&2
    exit 2
  fi
  case "$deploy_path" in
    */issue-tracker-uat) ;;
    *)
      echo "Refusing uat deploy: DEPLOY_PATH must end in issue-tracker-uat (got '$deploy_path')" >&2
      exit 2
      ;;
  esac
  if [ "$app_http_port" = "8000" ] || [ "$app_http_port" = "8443" ]; then
    echo "Refusing uat deploy: APP_HTTP_PORT $app_http_port is reserved for the dev app" >&2
    exit 2
  fi
fi

target_run() {
  if [ "$target_mode" = "local" ]; then
    bash -c "$1"
  else
    ssh "${ssh_opts[@]}" "$remote" "$1"
  fi
}

echo "Deploy mode: $target_mode"
echo "Deploy source ref: ${GITHUB_REF:-manual}"
echo "Deploy source sha: ${GITHUB_SHA:-manual}"
echo "Deploy target environment: ${deploy_environment:-unspecified}"
echo "Deploy path: $deploy_path"
echo "Health check: $app_healthcheck_url"

if [ -n "$expected_target_hostname" ]; then
  actual_hostname="$(target_run "hostname")"
  if [ "$actual_hostname" != "$expected_target_hostname" ]; then
    echo "Refusing $deploy_environment deploy: remote hostname '$actual_hostname' does not match expected '$expected_target_hostname'" >&2
    exit 2
  fi
fi

if [ -n "$remote_env_file" ]; then
  target_run "test -f '$remote_env_file'"
fi

if [ "$dry_run" = "1" ]; then
  echo "DRY RUN: all guards passed; would deploy ${GITHUB_SHA:-manual} to $deploy_path/releases/$release_id. No changes made."
  exit 0
fi

target_run "mkdir -p '$deploy_path/releases'"

unpack="mkdir -p '$deploy_path/releases/$release_id' && tar -xzf - -C '$deploy_path/releases/$release_id'"
if [ "$target_mode" = "local" ]; then
  # Committed tree only: uncommitted dev-checkout changes can never reach UAT.
  git archive --format=tar.gz "$expected_deploy_sha" | target_run "$unpack"
else
  tar \
    --exclude .git \
    --exclude .venv \
    --exclude .pytest_cache \
    --exclude .ruff_cache \
    --exclude exports \
    --exclude backups \
    --exclude '*.pyc' \
    -czf - . |
    target_run "$unpack"
fi

target_run \
  "set -euo pipefail
   if [ -n '$remote_env_file' ]; then
     set -a
     . '$remote_env_file'
     set +a
   fi
   if [ -e '$deploy_path/current' ] && [ ! -L '$deploy_path/current' ]; then
     mv '$deploy_path/current' '$deploy_path/current.pre-pipeline.$release_id'
   fi
   ln -sfn '$deploy_path/releases/$release_id' '$deploy_path/current'
   cd '$deploy_path/current'
   mkdir -p exports backups
   chmod -R u+rwX,go+rwX exports backups
   export APP_BASE_URL='$app_base_url'
   export APP_HTTP_PORT='$app_http_port'
   if [ -n '$compose_project_name' ]; then export COMPOSE_PROJECT_NAME='$compose_project_name'; fi
   if [ -n '$postgres_container_name' ]; then export POSTGRES_CONTAINER_NAME='$postgres_container_name'; fi
   echo "Compose project: \${COMPOSE_PROJECT_NAME:-<default>}"
   export APP_ENVIRONMENT='$app_environment'
   if [ '$deploy_environment' = 'prod' ]; then
     for required_name in APP_SECRET_KEY DATABASE_URL POSTGRES_PASSWORD; do
       case \"\$required_name\" in
         APP_SECRET_KEY) required_value=\"\${APP_SECRET_KEY:-}\" ;;
         DATABASE_URL) required_value=\"\${DATABASE_URL:-}\" ;;
         POSTGRES_PASSWORD) required_value=\"\${POSTGRES_PASSWORD:-}\" ;;
       esac
       if [ -z \"\$required_value\" ]; then
         echo \"Refusing prod deploy: \$required_name must be provided by REMOTE_ENV_FILE\" >&2
         exit 2
       fi
     done
   fi
   docker compose -f '$compose_file' build
   if [ '$skip_db_backup' != '1' ]; then
     mkdir -p '$deploy_path/backups/$release_id'
     docker compose -f '$compose_file' up -d postgres
     for attempt in 1 2 3 4 5 6 7 8 9 10; do
       if docker compose -f '$compose_file' exec -T postgres pg_isready \
         -U \"\${POSTGRES_USER:-issue_tracker}\" \
         -d \"\${POSTGRES_DB:-issue_tracker}\"; then
         break
       fi
       if [ \"\$attempt\" = 10 ]; then
         exit 1
       fi
       sleep 3
     done
     docker compose -f '$compose_file' exec -T postgres pg_dump \
       -U \"\${POSTGRES_USER:-issue_tracker}\" \
       -d \"\${POSTGRES_DB:-issue_tracker}\" \
       -Fc \
       -f '/tmp/issue-tracker-pre-migration.dump'
     docker compose -f '$compose_file' cp \
       postgres:/tmp/issue-tracker-pre-migration.dump \
       '$deploy_path/backups/$release_id/pre-migration.dump'
     docker compose -f '$compose_file' exec -T postgres rm -f '/tmp/issue-tracker-pre-migration.dump'
     test -s '$deploy_path/backups/$release_id/pre-migration.dump'
     echo 'Pre-migration backup: $deploy_path/backups/$release_id/pre-migration.dump'
   fi
   docker compose -f '$compose_file' run --rm app alembic upgrade head
   if [ '$run_tests' = '1' ]; then
     docker compose -f '$compose_file' run --rm app python -m pytest tests/
   fi
   if [ '$run_ruff' = '1' ]; then
     docker compose -f '$compose_file' run --rm app python -m ruff check --no-cache .
   fi
   docker compose -f '$compose_file' up -d
   for attempt in 1 2 3 4 5 6 7 8 9 10; do
     if curl -fsS '$app_healthcheck_url'; then
       break
     fi
     if [ \"\$attempt\" = 10 ]; then
       exit 1
     fi
     sleep 3
   done
   docker compose -f '$compose_file' run --rm app python -m issue_tracker.mcp.server --smoke
   if [ '$run_browser_uat' = '1' ]; then
     if [ -d tests/e2e ]; then
       docker compose -f '$compose_file' exec -e RUN_BROWSER_UAT=1 app python -m pytest tests/e2e/
     else
       echo 'Skipping browser UAT: tests/e2e/ is not present in this release'
     fi
   fi"

echo "Deployed ${GITHUB_SHA:-manual} to ${deploy_environment:-unspecified} ($target_mode) at $remote:$deploy_path/current"
