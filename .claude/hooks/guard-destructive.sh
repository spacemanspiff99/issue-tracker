#!/usr/bin/env bash
# PreToolUse guard for Bash. Blocks destructive or policy-violating commands that
# prefix-based permission rules miss (compound commands, flags inside docker
# compose run, SQL passed to psql). Exit 2 = block; stderr is shown to Claude.
# Policy source: AGENTS.md "Verification" and "Safety Boundaries".
set -euo pipefail

cmd="$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("command",""))')"

block() {
  echo "BLOCKED by .claude/hooks/guard-destructive.sh: $1" >&2
  echo "STOP and ask the user. See AGENTS.md Safety Boundaries. Do not work around this guard." >&2
  exit 2
}

shopt -s nocasematch
[[ "$cmd" =~ (^|[[:space:]\;\&\|])sudo[[:space:]] ]] && block "sudo is not allowed from an agent session."
[[ "$cmd" =~ alembic[[:space:]]+downgrade ]] && block "alembic downgrade: migrations are forward-only."
[[ "$cmd" =~ docker[[:space:]]+volume[[:space:]]+(rm|prune) ]] && block "Docker volume removal can destroy tracker data."
[[ "$cmd" =~ docker[[:space:]]+system[[:space:]]+prune ]] && block "Broad docker system prune requires explicit operator approval."
# compose down -v is allowed only for the disposable preflight project (documentation/guides/deployment.md).
if [[ "$cmd" =~ compose.*[[:space:]]down([[:space:]].*)?[[:space:]](-v|--volumes)([[:space:]]|$) ]] \
  && ! [[ "$cmd" =~ COMPOSE_PROJECT_NAME=issue_tracker_preflight[[:space:]] ]]; then
  block "compose down -v removes database volumes (only allowed with COMPOSE_PROJECT_NAME=issue_tracker_preflight)."
fi
[[ "$cmd" =~ (drop[[:space:]]+(database|schema|table)[[:space:]]|truncate[[:space:]]+table[[:space:]]|truncate[[:space:]]+[a-z_.\"]+[[:space:]]*(\;|cascade|restart|,)) ]] && block "Destructive SQL. Use /data-refresh with CONFIRM OVERWRITE <target>."
[[ "$cmd" =~ (dropdb|pg_restore.*(--clean|-c[[:space:]])) ]] && block "Database drop/overwrite. Use /data-refresh with CONFIRM OVERWRITE <target>."
[[ "$cmd" =~ git[[:space:]]+push.*(--force|[[:space:]]-f([[:space:]]|$)) ]] && block "Force-push is not allowed."
[[ "$cmd" =~ git[[:space:]]+reset[[:space:]]+--hard ]] && block "git reset --hard discards work."
[[ "$cmd" =~ git[[:space:]]+clean[[:space:]]+-[a-z]*f ]] && block "git clean -f deletes untracked files."
[[ "$cmd" =~ rm[[:space:]]+-[a-z]*r[a-z]*f|rm[[:space:]]+-[a-z]*f[a-z]*r ]] && block "rm -rf requires explicit user confirmation."
[[ "$cmd" =~ TEST_DATABASE_URL=.*(@postgres[:/]|192\.168\.10\.2[67]|issue-tracker\.akun) ]] && block "TEST_DATABASE_URL points at a real tracker database; tests drop_all."

# Host Playwright installs are banned; inside docker compose run/exec they are allowed.
if [[ "$cmd" =~ playwright[[:space:]]+install ]] && ! [[ "$cmd" =~ docker[[:space:]]+(compose[^\;\&\|]*[[:space:]](run|exec)|exec|build) ]]; then
  block "Host Playwright install. Browser deps belong in the Docker image."
fi

# UAT/prod workflow dispatch must pin the exact SHA.
if [[ "$cmd" =~ gh[[:space:]]+workflow[[:space:]]+run.*local-pipeline ]] && ! [[ "$cmd" =~ expected_deploy_sha=[0-9a-f]{40} ]]; then
  block "local-pipeline dispatch must pass -f expected_deploy_sha=<full 40-char SHA>. Use /uat-deploy."
fi

exit 0
