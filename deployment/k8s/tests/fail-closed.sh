#!/usr/bin/env bash
# No cluster needed. Runs deploy.sh and restore.sh against a stub kubectl that fails ONE chosen
# call per case (an API blip, auth error or timeout at that decision point). Every case must
# abort before anything irreversible: deploy.sh never applies the backup or migrate Job, and
# restore.sh never applies its restore Job. deploy.sh cases that fail after the maintenance
# window must also scale the old app back up.
#
# Usage: deployment/k8s/tests/fail-closed.sh   (needs a real kubectl on PATH for kustomize/set)
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
real_kubectl="$(command -v kubectl)"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
mkdir -p "$work/bin"
export STUB_LOG="$work/calls.log" REAL_KUBECTL="$real_kubectl"

# STUB_FAIL: a substring of the kubectl argument list; the first call containing it fails, as an
# API error would (every such call with STUB_FAIL_ALWAYS=1). Every other call behaves like a
# healthy cluster with the app running (1 replica): Jobs succeed and /health reports ok.
cat > "$work/bin/kubectl" <<'STUB'
#!/usr/bin/env bash
echo "kubectl $*" >> "$STUB_LOG"
args=" $* "
if [ -n "${STUB_FAIL:-}" ] && [[ "$args" == *"$STUB_FAIL"* ]] && { [ -n "${STUB_FAIL_ALWAYS:-}" ] || [ ! -e "$STUB_LOG.failed" ]; }; then
  : > "$STUB_LOG.failed"
  echo "Unable to connect to the server: stub failure for '$STUB_FAIL'" >&2
  exit 1
fi
case "$args" in
  *" kustomize "*|*" set env "*|*" --dry-run=client "*) exec "$REAL_KUBECTL" "$@" ;;
  *" config current-context "*) echo issue-tracker-uat ;;
  *" apply -f - "*) { echo "--- apply stdin:"; cat; } >> "$STUB_LOG" ;;
  *" get pods "*) [ -z "${STUB_PODS:-}" ] || echo "$STUB_PODS" ;;
  *" get job "*"jsonpath={.status.succeeded}/{.status.failed}"*) echo "1/" ;;
  *" get job "*"jsonpath={.status.succeeded}"*) echo 1 ;;
  *" exec deploy/issue-tracker "*) echo '{"ok":true,"database":"ok"}' ;;
  *" get deployment issue-tracker "*"-o name"*) echo deployment.apps/issue-tracker ;;
  *" get deployment issue-tracker "*"jsonpath={.spec.replicas}"*) echo "${STUB_REPLICAS:-1}" ;;
  *" get "*|*" apply "*|*" scale "*|*" delete "*|*" rollout "*|*" exec "*|*" logs "*|*" describe "*) : ;;
  *) echo "stub kubectl: unexpected call: $*" >&2; exit 1 ;;
esac
STUB
chmod +x "$work/bin/kubectl"
export PATH="$work/bin:$PATH"
export EXPECTED_CONTEXT=issue-tracker-uat DEPLOY_TIMEOUT_SECONDS=6 RESTORE_TIMEOUT_SECONDS=6
sha=0123456789abcdef0123456789abcdef01234567
failures=0

run_case() {  # run_case <deploy|restore> <description> <STUB_FAIL substring> [options]
  # options: scale-back = must end with the old app scaled back to 1; always = fail every matching
  # call (for bounded retry loops); optional = OK if the script never makes this call at all.
  local script="$1" desc="$2" fail="$3" opts=" ${4:-} " out="$work/out" always="" stub_fail="$3"
  [[ "$opts" == *" always "* ]] && always=1
  [ "$fail" != - ] || stub_fail=""   # "-": fail nothing; the case is driven by STUB_* state
  : > "$STUB_LOG"; rm -f "$STUB_LOG.failed"
  if [ "$script" = deploy ]; then
    STUB_FAIL="$stub_fail" STUB_FAIL_ALWAYS="$always" "$here/deploy.sh" uat ghcr.io/spacemanspiff99/issue-tracker:test "$sha" > "$out" 2>&1 && rc=0 || rc=$?
  else
    STUB_FAIL="$stub_fail" STUB_FAIL_ALWAYS="$always" CONFIRM=issue-tracker-uat "$here/restore.sh" uat /backups/daily/x.dump > "$out" 2>&1 && rc=0 || rc=$?
  fi
  local why=""
  if [ "$fail" != - ] && [ ! -e "$STUB_LOG.failed" ]; then
    if [[ "$opts" == *" optional "* ]] && [ "$rc" -eq 0 ]; then
      echo "n/a  [$script] $desc: the script no longer makes this call (and still succeeds)"
      return
    fi
    why="the stubbed call '$fail' was never made"
  fi
  [ -n "$why" ] || [ "$rc" -ne 0 ] || why="exited 0"
  if [ -z "$why" ] && [ "$script" = deploy ] && grep -qE 'apply .*component=(backup|migrate)' "$STUB_LOG"; then
    why="applied the backup or migrate Job"
  fi
  if [ -z "$why" ] && [ "$script" = restore ] && grep -q '^kind: Job$' "$STUB_LOG"; then
    why="applied the restore Job"
  fi
  if [ -z "$why" ] && [[ "$opts" == *" scale-back "* ]] \
    && [ "$(grep -o 'scale deployment/issue-tracker --replicas=[0-9]*' "$STUB_LOG" | tail -1)" != "scale deployment/issue-tracker --replicas=1" ]; then
    why="did not scale the previous app back to 1"
  fi
  if [ -n "$why" ]; then
    echo "FAIL [$script] $desc: $why"; sed 's/^/    /' "$out"; failures=$((failures + 1))
  else
    echo "ok   [$script] $desc: aborted (rc=$rc), nothing irreversible applied"
  fi
}

# deploy.sh decision points, in the order the script reaches them.
run_case deploy "kubectl context"                     "config current-context"
run_case deploy "app/db Secrets preflight"            "get secret issue-tracker-db issue-tracker-app"
run_case deploy "backup Job active? (NB-a)"           "get job issue-tracker-backup-predeploy"
run_case deploy "migrate Job active? (NB-a)"          "get job issue-tracker-migrate"
run_case deploy "restore Job active?"                 "get jobs -l app.kubernetes.io/component=restore"
run_case deploy "apply Postgres etc."                 "apply -f"
run_case deploy "Postgres rollout"                    "rollout status statefulset/issue-tracker-postgres"
run_case deploy "Postgres TCP wait (bounded)"         "psql -h 127.0.0.1 -X -q -At -U" always
run_case deploy "alembic_version before"              "exec -i issue-tracker-postgres-0"
run_case deploy "app Deployment exists?"              "get deployment issue-tracker --ignore-not-found -o name" optional
run_case deploy "app replicas"                        "get deployment issue-tracker --ignore-not-found -o jsonpath"
run_case deploy "scale app to 0"                      "scale deployment/issue-tracker --replicas=0" scale-back
run_case deploy "app pods gone?"                      "get pods -l app.kubernetes.io/component=web" scale-back
run_case deploy "delete previous Jobs"                "delete job issue-tracker-backup-predeploy issue-tracker-migrate --ignore-not-found --wait=true" scale-back

# NB-b: the Deployment is already at 0 replicas but a Terminating pod is still there (and may
# write). deploy.sh must wait it out and abort at the timeout, not start the backup.
STUB_REPLICAS=0 STUB_PODS=pod/issue-tracker-terminating run_case deploy "app at 0 with a lingering pod (NB-b)" -

# restore.sh decision points.
run_case restore "kubectl context"                    "config current-context"
run_case restore "backup Job active? (NB-a)"          "get job issue-tracker-backup-predeploy"
run_case restore "migrate Job active? (NB-a)"         "get job issue-tracker-migrate"
run_case restore "another restore active?"            "get jobs -l app.kubernetes.io/component=restore"
run_case restore "app replicas read"                  "get deployment issue-tracker --ignore-not-found -o jsonpath"
run_case restore "app Deployment exists? (B2)"        "get deployment issue-tracker --ignore-not-found -o name" optional
run_case restore "scale app to 0"                     "scale deployment/issue-tracker --replicas=0"
run_case restore "app pods gone?"                     "get pods -l app.kubernetes.io/component=web"
run_case restore "restore-script ConfigMap"           "create configmap issue-tracker-restore-script"

if [ "$failures" -ne 0 ]; then
  echo "$failures fail-closed case(s) FAILED" >&2
  exit 1
fi
echo "fail-closed checks passed"
