#!/usr/bin/env bash
# No cluster needed. Runs deploy.sh and restore.sh against a stub kubectl whose `get pods`
# fails (an API blip, auth error or timeout). Both scripts must treat "can't list the app's pods"
# as an error: deploy.sh never starts the backup or migration and brings the old app back, and
# restore.sh never creates its ConfigMap or Job.
#
# Usage: deployment/k8s/tests/fail-closed.sh   (needs a real kubectl on PATH for kustomize/set)
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
real_kubectl="$(command -v kubectl)"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
mkdir -p "$work/bin"
export STUB_LOG="$work/calls.log" REAL_KUBECTL="$real_kubectl"

cat > "$work/bin/kubectl" <<'STUB'
#!/usr/bin/env bash
echo "kubectl $*" >> "$STUB_LOG"
args=" $* "
case "$args" in
  *" kustomize "*|*" set env "*|*" --dry-run=client "*) exec "$REAL_KUBECTL" "$@" ;;
  *" config current-context "*) echo issue-tracker-uat ;;
  *" get pods "*) echo "The connection to the server was refused (stub)" >&2; exit 1 ;;
  *" get deployment issue-tracker "*"-o name"*) echo deployment.apps/issue-tracker ;;
  *" get deployment issue-tracker "*"jsonpath={.spec.replicas}"*) echo 1 ;;
  *" get "*|*" apply "*|*" scale "*|*" delete "*|*" rollout "*|*" exec "*|*" logs "*|*" describe "*) : ;;
  *) echo "stub kubectl: unexpected call: $*" >&2; exit 1 ;;
esac
STUB
chmod +x "$work/bin/kubectl"
export PATH="$work/bin:$PATH"
export EXPECTED_CONTEXT=issue-tracker-uat DEPLOY_TIMEOUT_SECONDS=10
sha=0123456789abcdef0123456789abcdef01234567

echo "== deploy.sh with an unreadable pod list"
: > "$STUB_LOG"
if "$here/deploy.sh" uat ghcr.io/spacemanspiff99/issue-tracker:test "$sha" > "$work/deploy.out" 2>&1; then
  cat "$work/deploy.out"; echo "FAIL: deploy.sh succeeded although the pod list could not be read" >&2; exit 1
fi
cat "$work/deploy.out"
grep -q 'could not list app pods' "$work/deploy.out"
grep -q '^deploy failed during: maintenance window$' "$work/deploy.out"
if grep -E 'apply .*component=(backup|migrate)' "$STUB_LOG"; then
  echo "FAIL: deploy.sh started a backup or migration without confirming the app stopped" >&2; exit 1
fi
[ "$(grep -o 'scale deployment/issue-tracker --replicas=[0-9]*' "$STUB_LOG" | tail -1)" = "scale deployment/issue-tracker --replicas=1" ] \
  || { echo "FAIL: deploy.sh did not bring the previous app back" >&2; exit 1; }
echo "ok: deploy.sh aborted before the backup and restored the previous app"

echo "== restore.sh with an unreadable pod list"
: > "$STUB_LOG"
if CONFIRM=issue-tracker-uat "$here/restore.sh" uat /backups/daily/x.dump > "$work/restore.out" 2>&1; then
  cat "$work/restore.out"; echo "FAIL: restore.sh succeeded although the pod list could not be read" >&2; exit 1
fi
cat "$work/restore.out"
grep -q 'could not list app pods' "$work/restore.out"
grep -q 'restore aborted before touching the database' "$work/restore.out"
if grep -E ' (apply|create) ' "$STUB_LOG"; then
  echo "FAIL: restore.sh created its ConfigMap or Job without confirming the app stopped" >&2; exit 1
fi
echo "ok: restore.sh aborted before any ConfigMap or Job"
echo "fail-closed checks passed"
