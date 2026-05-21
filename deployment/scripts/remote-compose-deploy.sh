#!/usr/bin/env bash
set -euo pipefail

target_host="${TARGET_HOST:?TARGET_HOST is required}"
target_user="${TARGET_USER:-akun}"
deploy_environment="${DEPLOY_ENVIRONMENT:-}"
expected_target_host="${EXPECTED_TARGET_HOST:-}"
expected_target_hostname="${EXPECTED_TARGET_HOSTNAME:-}"
deploy_path="${DEPLOY_PATH:-/home/akun/issue-tracker}"
compose_file="${COMPOSE_FILE:-deployment/docker-compose.local.yml}"
remote_env_file="${REMOTE_ENV_FILE:-}"
app_base_url="${APP_BASE_URL:-http://${target_host}:8000}"
app_http_port="${APP_HTTP_PORT:-8000}"
run_browser_uat="${RUN_BROWSER_UAT:-0}"
skip_db_backup="${SKIP_DB_BACKUP:-0}"
run_tests="${RUN_TESTS:-0}"
run_ruff="${RUN_RUFF:-0}"
release_id="${GITHUB_SHA:-manual}-$(date -u +%Y%m%d%H%M%S)"
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

case "$deploy_path" in
  /home/*/issue-tracker|/opt/issue-tracker|/srv/issue-tracker) ;;
  *)
    echo "Refusing unsafe DEPLOY_PATH: $deploy_path" >&2
    exit 2
    ;;
esac

if [ -n "$expected_target_hostname" ]; then
  actual_hostname="$(ssh "${ssh_opts[@]}" "$remote" "hostname")"
  if [ "$actual_hostname" != "$expected_target_hostname" ]; then
    echo "Refusing $deploy_environment deploy: remote hostname '$actual_hostname' does not match expected '$expected_target_hostname'" >&2
    exit 2
  fi
fi

if [ -n "$remote_env_file" ]; then
  ssh "${ssh_opts[@]}" "$remote" "test -f '$remote_env_file'"
fi

ssh "${ssh_opts[@]}" "$remote" "mkdir -p '$deploy_path/releases'"

tar \
  --exclude .git \
  --exclude .venv \
  --exclude .pytest_cache \
  --exclude .ruff_cache \
  --exclude exports \
  --exclude backups \
  --exclude '*.pyc' \
  -czf - . |
  ssh "${ssh_opts[@]}" "$remote" \
    "mkdir -p '$deploy_path/releases/$release_id' && tar -xzf - -C '$deploy_path/releases/$release_id'"

ssh "${ssh_opts[@]}" "$remote" \
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
   export APP_BASE_URL='$app_base_url'
   export APP_HTTP_PORT='$app_http_port'
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
       if docker compose -f '$compose_file' exec -T postgres pg_isready -U issue_tracker -d issue_tracker; then
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
     if curl -fsS '$app_base_url/health'; then
       break
     fi
     if [ \"\$attempt\" = 10 ]; then
       exit 1
     fi
     sleep 3
   done
   docker compose -f '$compose_file' run --rm app python -m issue_tracker.mcp.server --smoke
   if [ '$run_browser_uat' = '1' ]; then
     docker compose -f '$compose_file' exec -e RUN_BROWSER_UAT=1 app python -m pytest tests/e2e/
   fi"

echo "Deployed $release_id to $remote:$deploy_path/current"
