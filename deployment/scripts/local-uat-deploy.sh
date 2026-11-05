#!/usr/bin/env bash
# Deploy an exact pushed commit to UAT on this host (192.168.10.20, cursor-issue-tracker)
# as an isolated compose stack next to the live dev app. No GitHub Actions runner, no SSH.
#
# Usage:
#   deployment/scripts/local-uat-deploy.sh <full-commit-sha>             # deploy
#   DEPLOY_DRY_RUN=1 deployment/scripts/local-uat-deploy.sh <sha>        # guards only, no changes
#
# The source is `git archive <sha>`, so uncommitted changes in this checkout are never deployed.
# Code deploy only: the UAT volume is preserved (it starts empty on first deploy). Seeding UAT
# from dev is a separate destructive refresh that requires `CONFIRM OVERWRITE uat`.
set -euo pipefail

sha="${1:?usage: local-uat-deploy.sh <full-commit-sha>}"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"
git fetch --quiet origin

export TARGET_MODE=local
export DEPLOY_ENVIRONMENT=uat
export APP_ENVIRONMENT=uat
export EXPECTED_DEPLOY_SHA="$sha"
export TARGET_HOST=192.168.10.20
export EXPECTED_TARGET_HOST=192.168.10.20
export EXPECTED_TARGET_HOSTNAME=cursor-issue-tracker
export TARGET_USER="${USER:-akun}"
export DEPLOY_PATH=/home/akun/issue-tracker-uat
# Isolated from the live dev stack (project "deployment", container issue-tracker-postgres, port 8000).
export COMPOSE_PROJECT_NAME=issue_tracker_uat
export POSTGRES_CONTAINER_NAME=issue-tracker-uat-postgres
export APP_HTTP_PORT=8100
export APP_BASE_URL=https://uat.it.462111.xyz
export APP_HEALTHCHECK_URL=http://192.168.10.20:8100/health
export RUN_TESTS=1
export RUN_RUFF=1
export RUN_BROWSER_UAT=1
export SKIP_DB_BACKUP=0

exec bash deployment/scripts/remote-compose-deploy.sh
