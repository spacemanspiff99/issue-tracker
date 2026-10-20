#!/usr/bin/env bash
# Run the Playwright workflow suite (tests/e2e, issue 0014) inside the deployed app pod against
# the app on 127.0.0.1:8000, the same way remote-compose-deploy.sh RUN_BROWSER_UAT=1 does.
# Admin credentials come from the pod's own env (ADMIN_USERNAME, ADMIN_INITIAL_PASSWORD).
# Skips with a notice when the deployed image has no tests/e2e (0014 not merged yet).
#
# Usage: deployment/k8s/e2e.sh <namespace>
set -euo pipefail
ns="${1:?usage: e2e.sh <namespace>}"
[ "$ns" = issue-tracker ] && { echo "refusing to run e2e against production" >&2; exit 2; }

if ! kubectl -n "$ns" exec deploy/issue-tracker -c app -- test -d /app/tests/e2e; then
  echo "SKIP: deployed image has no tests/e2e (issue 0014 not merged); browser suite not run"
  exit 0
fi
kubectl -n "$ns" exec deploy/issue-tracker -c app -- \
  env RUN_BROWSER_UAT=1 E2E_BASE_URL=http://127.0.0.1:8000 \
  python -m pytest -p no:cacheprovider -rfEX tests/e2e/
