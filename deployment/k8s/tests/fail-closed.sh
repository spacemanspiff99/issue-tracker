#!/usr/bin/env bash
# No cluster needed. Runs deploy.sh and restore.sh against a stub kubectl that fails chosen calls
# (an API blip, auth error or timeout at that decision point). Cases before the Jobs: the script
# must abort before applying the backup/migrate Job (deploy.sh) or the restore Job (restore.sh).
# Cases after the Jobs: the app must not be scaled up unless the script has proven it is safe.
#
# Usage: deployment/k8s/tests/fail-closed.sh   (needs a real kubectl on PATH for kustomize/set)
#        FC_ONLY="<text>" runs only the matching cases (used by fail-closed-mutations.sh).
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
real_kubectl="$(command -v kubectl)"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
mkdir -p "$work/bin"
export STUB_LOG="$work/calls.log" REAL_KUBECTL="$real_kubectl"

# STUB_FAIL: "|"-separated entries "[N:]substring". Entry k fails the Nth (default 1st) kubectl call
# whose arguments contain the substring, as an API error would; with STUB_FAIL_ALWAYS=1 it fails
# every such call. Otherwise the stub is a healthy cluster with the app at STUB_REPLICAS (1):
# Jobs report STUB_JOB_STATUS ("succeeded/failed", default "1/"), Job logs print STUB_LOGS, and
# /health reports ok. STUB_RESTORE_ACTIVE_FROM=N: from the Nth "restore Jobs active?" read on,
# another restore Job reports active (one started meanwhile).
cat > "$work/bin/kubectl" <<'STUB'
#!/usr/bin/env bash
echo "kubectl $*" >> "$STUB_LOG"
args=" $* "
if [ -n "${STUB_FAIL:-}" ]; then
  IFS='|' read -r -a entries <<< "$STUB_FAIL"
  for k in "${!entries[@]}"; do
    entry="${entries[$k]}" nth=1
    if [[ "$entry" =~ ^([0-9]+):(.*)$ ]]; then nth="${BASH_REMATCH[1]}" entry="${BASH_REMATCH[2]}"; fi
    [[ "$args" == *"$entry"* ]] || continue
    seen=$(( $(cat "$STUB_LOG.seen$k" 2> /dev/null || echo 0) + 1 ))
    echo "$seen" > "$STUB_LOG.seen$k"
    if [ "$seen" -eq "$nth" ] || { [ -n "${STUB_FAIL_ALWAYS:-}" ] && [ "$seen" -ge "$nth" ]; }; then
      echo "$k" >> "$STUB_LOG.failed"
      echo "Unable to connect to the server: stub failure for '$entry'" >&2
      exit 1
    fi
  done
fi
case "$args" in
  *" kustomize "*|*" set env "*|*" --dry-run=client "*) exec "$REAL_KUBECTL" "$@" ;;
  *" config current-context "*) echo issue-tracker-uat ;;
  *" apply -f - "*|*" create -f - "*) { echo "--- apply stdin:"; cat; } >> "$STUB_LOG" ;;
  *" get jobs -l app.kubernetes.io/component=restore "*)
    n=$(( $(cat "$STUB_LOG.restore-reads" 2> /dev/null || echo 0) + 1 )); echo "$n" > "$STUB_LOG.restore-reads"
    [ -z "${STUB_RESTORE_ACTIVE_FROM:-}" ] || [ "$n" -lt "$STUB_RESTORE_ACTIVE_FROM" ] || echo 1 ;;
  *" get pods "*) [ -z "${STUB_PODS:-}" ] || echo "$STUB_PODS" ;;
  *" get job "*"jsonpath={.status.succeeded}/{.status.failed}"*) echo "${STUB_JOB_STATUS:-1/}" ;;
  *" logs job/"*) printf '%s\n' "${STUB_LOGS:-}" ;;
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

run_case() {  # run_case <deploy|restore> <description> <STUB_FAIL entries or -> [options]
  # options:
  #   always       fail every matching call (for bounded retry loops)
  #   after-backup the case fails after the backup Job: only the migrate Job must not be applied
  #   after-jobs   the case fails after all Jobs were applied (deploy migrate / restore Job)
  #   scale-back   must end with the old app scaled back to 1
  #   no-scale-up  must never scale the app above 0
  #   exit0        the script must exit 0 (a successful restore) instead of failing
  # RESTORE_FLAGS (env) adds restore.sh options, e.g. --keep-app-down. EXPECT_OUTPUT (env): text
  # the script's output must contain. EXPECT_REPLICAS (env): the last scale must be to this count,
  # and no scale may go above it.
  local script="$1" desc="$2" fail="$3" opts=" ${4:-} " out="$work/out" always="" stub_fail="$3"
  # FC_ONLY (env): run only cases whose "[script] description" contains this text.
  [ -z "${FC_ONLY:-}" ] || [[ "[$script] $desc" == *"$FC_ONLY"* ]] || return 0
  [[ "$opts" == *" always "* ]] && always=1
  [ "$fail" != - ] || stub_fail=""   # "-": fail nothing; the case is driven by STUB_* state
  : > "$STUB_LOG"; rm -f "$STUB_LOG".failed "$STUB_LOG".seen* "$STUB_LOG".restore-reads
  if [ "$script" = deploy ]; then
    STUB_FAIL="$stub_fail" STUB_FAIL_ALWAYS="$always" "$here/deploy.sh" uat ghcr.io/spacemanspiff99/issue-tracker:test "$sha" > "$out" 2>&1 && rc=0 || rc=$?
  else
    # shellcheck disable=SC2086
    STUB_FAIL="$stub_fail" STUB_FAIL_ALWAYS="$always" CONFIRM=issue-tracker-uat "$here/restore.sh" uat /backups/daily/x.dump ${RESTORE_FLAGS:-} > "$out" 2>&1 && rc=0 || rc=$?
  fi
  local why="" n_entries=0
  if [ -n "$stub_fail" ]; then
    n_entries="$(awk -F'|' '{print NF}' <<< "$stub_fail")"
    [ "$(sort -u "$STUB_LOG.failed" 2> /dev/null | wc -l)" -eq "$n_entries" ] \
      || why="not every stubbed call in '$fail' was made"
  fi
  if [[ "$opts" == *" exit0 "* ]]; then
    [ -n "$why" ] || [ "$rc" -eq 0 ] || why="exited $rc"
  else
    [ -n "$why" ] || [ "$rc" -ne 0 ] || why="exited 0"
  fi
  if [ -z "$why" ] && [ "$script" = deploy ]; then
    if [[ "$opts" == *" after-jobs "* ]]; then :
    elif [[ "$opts" == *" after-backup "* ]]; then
      grep -qE 'apply .*component=migrate' "$STUB_LOG" && why="applied the migrate Job"
    else
      grep -qE 'apply .*component=(backup|migrate)' "$STUB_LOG" && why="applied the backup or migrate Job"
    fi
  fi
  if [ -z "$why" ] && [ "$script" = restore ] && [[ "$opts" != *" after-jobs "* ]] && grep -q '^kind: Job$' "$STUB_LOG"; then
    why="applied the restore Job"
  fi
  if [ -z "$why" ] && [ -n "${EXPECT_OUTPUT:-}" ] && ! grep -qF "$EXPECT_OUTPUT" "$out"; then
    why="output lacks: $EXPECT_OUTPUT"
  fi
  if [ -z "$why" ] && [[ "$opts" == *" no-scale-up "* ]] && grep -qE 'scale deployment/issue-tracker --replicas=[1-9]' "$STUB_LOG"; then
    why="scaled the app up: $(grep -oE 'scale deployment/issue-tracker --replicas=[0-9]+' "$STUB_LOG" | tr '\n' ' ')"
  fi
  if [ -z "$why" ] && [[ "$opts" == *" scale-back "* ]] \
    && [ "$(grep -o 'scale deployment/issue-tracker --replicas=[0-9]*' "$STUB_LOG" | tail -1)" != "scale deployment/issue-tracker --replicas=1" ]; then
    why="did not scale the previous app back to 1"
  fi
  if [ -z "$why" ] && [ -n "${EXPECT_REPLICAS:-}" ]; then
    local scales last
    scales="$(grep -oE 'scale deployment/issue-tracker --replicas=[0-9]+' "$STUB_LOG" | sed 's/.*=//' | tr '\n' ' ')"
    last="${scales% }"; last="${last##* }"
    for n in $scales; do [ "$n" -le "$EXPECT_REPLICAS" ] || why="scaled above $EXPECT_REPLICAS: $scales"; done
    [ -n "$why" ] || [ "$last" = "$EXPECT_REPLICAS" ] || why="did not end at $EXPECT_REPLICAS replica(s): ${scales:-no scale}"
  fi
  if [ -n "$why" ]; then
    echo "FAIL [$script] $desc: $why"; sed 's/^/    /' "$out"; failures=$((failures + 1))
  else
    echo "ok   [$script] $desc: rc=$rc, fails closed"
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
run_case deploy "app Deployment exists?"              "get deployment issue-tracker --ignore-not-found -o name"
run_case deploy "app replicas"                        "get deployment issue-tracker --ignore-not-found -o jsonpath"
run_case deploy "scale app to 0"                      "scale deployment/issue-tracker --replicas=0" scale-back
run_case deploy "app pods gone?"                      "get pods -l app.kubernetes.io/component=web" scale-back
run_case deploy "delete previous Jobs"                "delete job issue-tracker-backup-predeploy issue-tracker-migrate --ignore-not-found --wait=true" scale-back

# NB-b: the Deployment is already at 0 replicas but a Terminating pod is still there (and may
# write). deploy.sh must wait it out and abort at the timeout, not start the backup.
STUB_REPLICAS=0 STUB_PODS=pod/issue-tracker-terminating run_case deploy "app at 0 with a lingering pod (NB-b)" -

# deploy.sh after the Jobs were applied (wait_job reads, then on_failure's own checks).
wait_backup="get job issue-tracker-backup-predeploy -o jsonpath={.status.succeeded}"
run_case deploy "wait_job read fails (backup)"        "$wait_backup" "after-backup scale-back"
run_case deploy "wait_job read fails (migrate)"       "get job issue-tracker-migrate -o jsonpath={.status.succeeded}" "after-jobs scale-back"
run_case deploy "…and on_failure can't list Jobs"     "$wait_backup|get job issue-tracker-backup-predeploy issue-tracker-migrate --ignore-not-found -o name" "after-backup no-scale-up"
run_case deploy "…and on_failure can't read version"  "$wait_backup|2:exec -i issue-tracker-postgres-0" "after-backup no-scale-up"

# restore.sh decision points.
run_case restore "kubectl context"                    "config current-context"
run_case restore "backup Job active? (NB-a)"          "get job issue-tracker-backup-predeploy"
run_case restore "migrate Job active? (NB-a)"         "get job issue-tracker-migrate"
run_case restore "another restore active?"            "get jobs -l app.kubernetes.io/component=restore"
run_case restore "app replicas read"                  "get deployment issue-tracker --ignore-not-found -o jsonpath"
run_case restore "scale app to 0"                     "scale deployment/issue-tracker --replicas=0"
run_case restore "app pods gone?"                     "get pods -l app.kubernetes.io/component=web"
run_case restore "restore-script ConfigMap"           "create configmap issue-tracker-restore-script"

# restore.sh after the Job was applied: status, logs and delete must each fail closed. Logs that
# show a committed same-revision restore, so a wrongly assumed success would scale the app up.
same=$'alembic_version before restore: 0004_x\nrestore committed\nalembic_version after restore: 0004_x'
older=$'alembic_version before restore: 0004_x\nrestore committed\nalembic_version after restore: 0003_y'
STUB_LOGS="$same" run_case restore "Job status unreadable (timeout)" "get job issue-tracker-restore-" "always after-jobs no-scale-up"
STUB_JOB_STATUS=/1 run_case restore "Job failed, logs unreadable" "logs job/issue-tracker-restore-" "after-jobs no-scale-up"
STUB_JOB_STATUS=/ EXPECT_OUTPUT="could NOT be confirmed deleted" \
  run_case restore "timeout, Job delete fails" "delete job issue-tracker-restore-" "after-jobs no-scale-up"
# Control: failed before COMMIT with readable logs and the app at 1 -> back to 1 (not a fail-open).
STUB_JOB_STATUS=/1 run_case restore "Job failed before COMMIT (control)" - "after-jobs scale-back"
# B1 (round 3): the app was at 0 before the restore; a pre-COMMIT failure must leave it at 0,
# with and without --keep-app-down. And --keep-app-down at 1 replica must also stay at 0.
STUB_REPLICAS=0 STUB_JOB_STATUS=/1 RESTORE_FLAGS=--keep-app-down run_case restore "app at 0, --keep-app-down, failed before COMMIT (B1)" - "after-jobs no-scale-up"
STUB_REPLICAS=0 STUB_JOB_STATUS=/1 run_case restore "app at 0, failed before COMMIT (B1)" - "after-jobs no-scale-up"
STUB_JOB_STATUS=/1 RESTORE_FLAGS=--keep-app-down run_case restore "--keep-app-down, failed before COMMIT (B1)" - "after-jobs no-scale-up"

# Issue 0042. A successful restore returns the app to its previous count (never above, 0 stays 0)
# only when the Job's logs show the same alembic_version before and after (N1, N3).
STUB_LOGS="$same" EXPECT_REPLICAS=1 run_case restore "success, same schema, app at 1 -> 1 (N3)" - "after-jobs exit0"
STUB_LOGS="$same" STUB_REPLICAS=2 EXPECT_REPLICAS=2 run_case restore "success, same schema, app at 2 -> 2 (N3)" - "after-jobs exit0"
STUB_LOGS="$same" STUB_REPLICAS=0 run_case restore "success, app at 0 stays at 0 (N3)" - "after-jobs exit0 no-scale-up"
STUB_JOB_STATUS=/1 STUB_REPLICAS=2 EXPECT_REPLICAS=2 run_case restore "failed before COMMIT, app at 2 -> 2 (N3)" - after-jobs
STUB_LOGS="$older" EXPECT_OUTPUT="from '0004_x' to '0003_y'" \
  run_case restore "success, schema changed: app left at 0 (N1)" - "after-jobs no-scale-up"
STUB_LOGS="restore committed" run_case restore "success, versions not in the logs: app left at 0 (N1)" - "after-jobs no-scale-up"
run_case restore "success, logs unreadable: app left at 0 (N1)" "logs job/issue-tracker-restore-" "after-jobs no-scale-up"
# N4: another restore starts while this one is stopping the app; re-checked just before the Job.
STUB_RESTORE_ACTIVE_FROM=2 run_case restore "another restore started meanwhile (N4)" -

if [ "$failures" -ne 0 ]; then
  echo "$failures fail-closed case(s) FAILED" >&2
  exit 1
fi
echo "fail-closed checks passed"
