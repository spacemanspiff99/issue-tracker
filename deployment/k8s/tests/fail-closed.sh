#!/usr/bin/env bash
# No cluster needed. Runs deploy.sh and restore.sh against a stub kubectl that fails chosen calls
# (an API blip, auth error or timeout at that decision point). Cases before the Jobs: the script
# must abort before applying the backup/migrate Job (deploy.sh) or the restore Job (restore.sh).
# Cases after the Jobs: the app must not be scaled up unless the script has proven it is safe.
#
# Usage: deployment/k8s/tests/fail-closed.sh   (needs a real kubectl on PATH for kustomize/set)
#        FC_ONLY="<text>" runs only the matching cases (used by fail-closed-mutations.sh).
set -euo pipefail
command -v kubectl > /dev/null || { echo "fail-closed.sh needs kubectl on PATH (for kustomize and set env)" >&2; exit 2; }
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
# another restore Job reports active (one started meanwhile). The restore lock ConfigMap can be
# created once per case (STUB_LOCK_HELD=1: it already exists); its data.job reads back as the
# creator's, or as STUB_LOCK_HOLDER (another run took it meanwhile). STUB_RESTORE_PODS: "name phase"
# lines, returned from the STUB_RESTORE_PODS_FROM-th (default 1st) restore-pod list on.
cat > "$work/bin/kubectl" <<'STUB'
#!/usr/bin/env bash
echo "kubectl $*" >> "$STUB_LOG"
args=" $* "
# STUB_SIGNAL_ON: the first call whose arguments contain this sends TERM and INT to the calling
# script, as a cancelled CI run (or a second Ctrl-C) would, and then still answers.
if [ -n "${STUB_SIGNAL_ON:-}" ] && [[ "$args" == *"$STUB_SIGNAL_ON"* ]] && [ ! -e "$STUB_LOG.signalled" ]; then
  touch "$STUB_LOG.signalled"; kill -TERM "$PPID"; kill -INT "$PPID"; sleep 1
fi
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
      # STUB_PARTIAL_LOGS=1: a failing `logs` call first prints STUB_LOGS (a stream cut off midway).
      [[ -z "${STUB_PARTIAL_LOGS:-}" || "$args" != *" logs "* ]] || printf '%s\n' "${STUB_LOGS:-}"
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
  *" create configmap issue-tracker-restore-lock "*)
    if [ -n "${STUB_LOCK_HELD:-}" ] || [ -e "$STUB_LOG.lock" ]; then
      echo 'Error from server (AlreadyExists): configmaps "issue-tracker-restore-lock" already exists' >&2; exit 1
    fi
    [[ "$args" =~ --from-literal=job=([^ ]+) ]] && echo "${BASH_REMATCH[1]}" > "$STUB_LOG.lock" ;;
  *" get configmap issue-tracker-restore-lock "*)
    if [ -n "${STUB_LOCK_HOLDER:-}" ]; then echo "$STUB_LOCK_HOLDER"; else cat "$STUB_LOG.lock" 2> /dev/null || true; fi ;;
  *" delete configmap issue-tracker-restore-lock "*) rm -f "$STUB_LOG.lock" ;;
  *" get pods -l app.kubernetes.io/component=restore "*)
    n=$(( $(cat "$STUB_LOG.pod-reads" 2> /dev/null || echo 0) + 1 )); echo "$n" > "$STUB_LOG.pod-reads"
    [ -z "${STUB_RESTORE_PODS:-}" ] || [ "$n" -lt "${STUB_RESTORE_PODS_FROM:-1}" ] || printf '%s\n' "$STUB_RESTORE_PODS" ;;
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
  #   lock-kept    the restore lock must not be released (not taken, or the Job may still run)
  #   lock-released the restore lock must be released before the script ends
  # RESTORE_FLAGS (env) adds restore.sh options, e.g. --keep-app-down. EXPECT_OUTPUT (env): text
  # the script's output must contain. EXPECT_REPLICAS (env): the last scale must be to this count,
  # and no scale may go above it. EXPECT_LOG (env): text the kubectl calls (and stdin) must contain.
  local script="$1" desc="$2" fail="$3" opts=" ${4:-} " out="$work/out" always="" stub_fail="$3"
  # FC_ONLY (env): run only cases whose "[script] description" contains this text.
  [ -z "${FC_ONLY:-}" ] || [[ "[$script] $desc" == *"$FC_ONLY"* ]] || return 0
  [[ "$opts" == *" always "* ]] && always=1
  [ "$fail" != - ] || stub_fail=""   # "-": fail nothing; the case is driven by STUB_* state
  : > "$STUB_LOG"; rm -f "$STUB_LOG".failed "$STUB_LOG".seen* "$STUB_LOG".restore-reads "$STUB_LOG".lock "$STUB_LOG".pod-reads "$STUB_LOG".signalled
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
  if [ -z "$why" ] && [ -n "${EXPECT_LOG:-}" ] && ! grep -qF -- "$EXPECT_LOG" "$STUB_LOG"; then
    why="kubectl calls lack: $EXPECT_LOG"
  fi
  if [ -z "$why" ] && [[ "$opts" == *" lock-kept "* ]] && grep -q 'delete configmap issue-tracker-restore-lock' "$STUB_LOG"; then
    why="released the restore lock"
  fi
  if [ -z "$why" ] && [[ "$opts" == *" lock-released "* ]] && ! grep -q 'delete configmap issue-tracker-restore-lock' "$STUB_LOG"; then
    why="did not release the restore lock"
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
# A failure the Job saw: it re-read alembic_version on the way out, and it is unchanged.
failed_same=$'alembic_version before restore: 0004_x\nalembic_version after failed restore: 0004_x'
STUB_LOGS="$same" run_case restore "Job status unreadable (timeout)" "get job issue-tracker-restore-" "always after-jobs no-scale-up"
STUB_JOB_STATUS=/1 STUB_PARTIAL_LOGS=1 STUB_LOGS="$failed_same" run_case restore "Job failed, logs unreadable" "logs job/issue-tracker-restore-" "after-jobs no-scale-up"
STUB_JOB_STATUS=/ EXPECT_OUTPUT="could NOT be confirmed deleted" \
  run_case restore "timeout, Job delete fails" "delete job issue-tracker-restore-" "after-jobs no-scale-up"
# Control: failed before COMMIT, readable logs, version unchanged, app at 1 -> back to 1.
STUB_LOGS="$failed_same" STUB_JOB_STATUS=/1 EXPECT_OUTPUT="revision unchanged (0004_x)" \
  run_case restore "Job failed before COMMIT (control)" - "after-jobs scale-back"
# B1 (round 3): the app was at 0 before the restore; a pre-COMMIT failure must leave it at 0,
# with and without --keep-app-down. And --keep-app-down at 1 replica must also stay at 0.
STUB_LOGS="$failed_same" STUB_REPLICAS=0 STUB_JOB_STATUS=/1 RESTORE_FLAGS=--keep-app-down run_case restore "app at 0, --keep-app-down, failed before COMMIT (B1)" - "after-jobs no-scale-up"
STUB_LOGS="$failed_same" STUB_REPLICAS=0 STUB_JOB_STATUS=/1 run_case restore "app at 0, failed before COMMIT (B1)" - "after-jobs no-scale-up"
STUB_LOGS="$failed_same" STUB_JOB_STATUS=/1 RESTORE_FLAGS=--keep-app-down run_case restore "--keep-app-down, failed before COMMIT (B1)" - "after-jobs no-scale-up"

# Issue 0042. A successful restore returns the app to its previous count (never above, 0 stays 0)
# only when the Job's logs show the same alembic_version before and after (N1, N3).
STUB_LOGS="$same" EXPECT_REPLICAS=1 run_case restore "success, same schema, app at 1 -> 1 (N3)" - "after-jobs exit0"
STUB_LOGS="$same" STUB_REPLICAS=2 EXPECT_REPLICAS=2 run_case restore "success, same schema, app at 2 -> 2 (N3)" - "after-jobs exit0"
STUB_LOGS="$same" STUB_REPLICAS=0 run_case restore "success, app at 0 stays at 0 (N3)" - "after-jobs exit0 no-scale-up"
STUB_LOGS="$failed_same" STUB_JOB_STATUS=/1 STUB_REPLICAS=2 EXPECT_REPLICAS=2 run_case restore "failed before COMMIT, app at 2 -> 2 (N3)" - after-jobs
STUB_LOGS="$older" EXPECT_OUTPUT="from '0004_x' to '0003_y'" \
  run_case restore "success, schema changed: app left at 0 (N1)" - "after-jobs no-scale-up"
STUB_LOGS="restore committed" run_case restore "success, versions not in the logs: app left at 0 (N1)" - "after-jobs no-scale-up"
run_case restore "success, logs unreadable: app left at 0 (N1)" "logs job/issue-tracker-restore-" "after-jobs no-scale-up"
# N4: another restore starts while this one is stopping the app; re-checked just before the Job.
STUB_RESTORE_ACTIVE_FROM=2 run_case restore "another restore started meanwhile (N4)" -

# Issue 0047.
# N-1: the restore lock. Taken before anything changes; never released by a run that didn't take
# it; released on exit, except while this run's Job may still be running.
STUB_LOCK_HELD=1 EXPECT_OUTPUT="could not take the restore lock" \
  run_case restore "lock already held: refuses, leaves the lock (N-1)" - lock-kept
run_case restore "lock create fails: refuses, leaves the lock (N-1)" "create configmap issue-tracker-restore-lock" lock-kept
STUB_LOGS="$same" run_case restore "lock released after a successful restore (N-1)" - "after-jobs exit0 lock-released"
run_case restore "lock released when the app can't be stopped (N-1)" "scale deployment/issue-tracker --replicas=0" lock-released
STUB_JOB_STATUS=/ EXPECT_OUTPUT="restore lock kept" \
  run_case restore "lock kept while the Job may still run (N-1)" "delete job issue-tracker-restore-" "after-jobs no-scale-up lock-kept"
# N-2 / 0048 #1: no restore pod may be live (one may hold a pin), checked before the lock and again
# just before the Job. Pods that finished don't count.
live_pods=$'issue-tracker-restore-1-live Running\nissue-tracker-restore-0-old Failed'
STUB_RESTORE_PODS="$live_pods" EXPECT_OUTPUT="restore pod(s) still running" \
  run_case restore "live restore pod without a Job: refuses before anything (0048 #1)" - lock-kept
STUB_RESTORE_PODS="$live_pods" STUB_RESTORE_PODS_FROM=2 EXPECT_OUTPUT="restore pod(s) started" \
  run_case restore "restore pod started meanwhile: refuses before the Job (0048 #1)" - "no-scale-up lock-released"
STUB_LOGS="$same" STUB_RESTORE_PODS=$'issue-tracker-restore-0-old Succeeded\nissue-tracker-restore-0-older Failed' \
  run_case restore "finished restore pods don't block (0048 #1)" - "after-jobs exit0"
run_case restore "restore pods unreadable before the lock (N-2)" "get pods -l app.kubernetes.io/component=restore" lock-kept
run_case restore "restore pods unreadable after the lock (N-2)" "2:get pods -l app.kubernetes.io/component=restore" lock-released
# N-3: after a failure the app comes back only if the version re-read on the way out is unchanged.
STUB_JOB_STATUS=/1 STUB_LOGS=$'alembic_version before restore: 0004_x\nalembic_version after failed restore: 0003_y' \
  EXPECT_OUTPUT="after the failure '0003_y'" run_case restore "failed, version changed: app left at 0 (N-3)" - "after-jobs no-scale-up"
STUB_JOB_STATUS=/1 STUB_LOGS="alembic_version before restore: 0004_x" \
  run_case restore "failed, no version after the failure (killed): app left at 0 (N-3)" - "after-jobs no-scale-up"
# N-4: exactly one line per version; duplicates (however consistent) count as unknown.
dup2=$'alembic_version before restore: 0004_x\nalembic_version before restore: 0004_x\nrestore committed\nalembic_version after restore: 0004_x\nalembic_version after restore: 0004_x'
STUB_LOGS="$dup2" run_case restore "success, duplicate version lines: app left at 0 (N-4)" - "after-jobs no-scale-up"
STUB_JOB_STATUS=/1 STUB_LOGS=$'alembic_version before restore: 0004_x\nalembic_version before restore: 0004_x\nalembic_version after failed restore: 0004_x\nalembic_version after failed restore: 0004_x' \
  run_case restore "failed, duplicate version lines: app left at 0 (N-4)" - "after-jobs no-scale-up"

# 0048 #2: the lock is released only by its holder: if data.job names another run, leave it.
STUB_LOGS="$same" STUB_LOCK_HOLDER=someone-else EXPECT_OUTPUT="not by this run" \
  run_case restore "lock now held by another run: not released (0048 #2)" - "after-jobs exit0 lock-kept"
STUB_LOGS="$same" run_case restore "lock holder unreadable: not released (0048 #2)" "get configmap issue-tracker-restore-lock" "after-jobs exit0 lock-kept"
# 0048 #3: deploy.sh takes the same lock, and releases it like restore.sh does.
STUB_LOCK_HELD=1 EXPECT_OUTPUT="could not take the restore lock" \
  run_case deploy "deploy: lock held by a restore: refuses (0048 #3)" - lock-kept
run_case deploy "deploy: lock create fails: refuses (0048 #3)" "create configmap issue-tracker-restore-lock" lock-kept
run_case deploy "deploy: lock released after a successful deploy (0048 #3)" - "after-jobs exit0 lock-released"
run_case deploy "deploy: lock released after a failure before the Jobs (0048 #3)" "rollout status statefulset/issue-tracker-postgres" lock-released
run_case deploy "deploy: lock released when the Jobs are confirmed gone (0048 #3)" "$wait_backup" "after-backup scale-back lock-released"
EXPECT_OUTPUT="restore lock kept" run_case deploy "deploy: lock kept when the Jobs may still run (0048 #3)" \
  "$wait_backup|get job issue-tracker-backup-predeploy issue-tracker-migrate --ignore-not-found -o name" "after-backup no-scale-up lock-kept"
STUB_LOCK_HOLDER=someone-else EXPECT_OUTPUT="not by this deploy" \
  run_case deploy "deploy: lock now held by another run: not released (0048 #2)" - "after-jobs exit0 lock-kept"

# Issue 0049: deploy.sh refuses while a restore pod is live without an active Job, before the
# lock and again (with the app stopped) just before the backup Job.
STUB_RESTORE_PODS="$live_pods" EXPECT_OUTPUT="restore pod(s) still running" \
  run_case deploy "deploy: live restore pod: refuses before anything (0049)" - lock-kept
STUB_RESTORE_PODS="$live_pods" STUB_RESTORE_PODS_FROM=2 EXPECT_OUTPUT="restore pod(s) started in" \
  run_case deploy "deploy: restore pod started meanwhile: refuses before the backup (0049)" - "scale-back lock-released"
STUB_RESTORE_PODS=$'issue-tracker-restore-0-old Succeeded\nissue-tracker-restore-0-older Failed' \
  run_case deploy "deploy: finished restore pods don't block (0049)" - "after-jobs exit0 lock-released"
run_case deploy "deploy: restore pods unreadable before the lock (0049)" "get pods -l app.kubernetes.io/component=restore" lock-kept
run_case deploy "deploy: restore pods unreadable before the backup (0049)" "2:get pods -l app.kubernetes.io/component=restore" "scale-back lock-released"
# Issue 0050: TERM + INT arrive while on_failure is deleting the Jobs. It must still finish: print
# its summary, bring the old app back (Jobs gone, version unchanged) and release the lock.
STUB_SIGNAL_ON="--cascade=foreground" EXPECT_OUTPUT="restoring the previous app" \
  run_case deploy "deploy: TERM+INT during on_failure's cleanup: still finishes (0050)" "$wait_backup" "after-backup scale-back lock-released"
STUB_SIGNAL_ON="get job issue-tracker-backup-predeploy issue-tracker-migrate --ignore-not-found -o name" EXPECT_OUTPUT="restoring the previous app" \
  run_case deploy "deploy: TERM+INT during on_failure's Job check: still finishes (0050)" "$wait_backup" "after-backup scale-back lock-released"

# restore-job.sh itself, against stub psql/pg_dump/pg_restore and a scratch /backups (BACKUPS_ROOT).
mkdir -p "$work/pgbin"
cat > "$work/pgbin/psql" <<'STUB'
#!/usr/bin/env bash
case " $* " in
  *"to_regclass('public.alembic_version')"*) echo t ;;
  *string_agg*) cat "$PG_STATE/version" ;;
  *) cat > /dev/null
     if [ -n "${PG_FAIL_TX:-}" ]; then echo "ERROR: stub failure inside the transaction" >&2; exit 3; fi
     cp "$PG_STATE/dump_version" "$PG_STATE/version" ;;
esac
STUB
cat > "$work/pgbin/pg_restore" <<'STUB'
#!/usr/bin/env bash
case " $* " in *" -l "*) echo "1; 0 0 TABLE DATA public projects owner" ;; *) echo "-- stub SQL" ;; esac
STUB
cat > "$work/pgbin/pg_dump" <<'STUB'
#!/usr/bin/env bash
while [ $# -gt 0 ]; do [ "$1" = -f ] && { echo stub-dump > "$2"; exit 0; }; shift; done
exit 1
STUB
chmod +x "$work/pgbin"/*
run_job_case() {  # run_job_case <description> <ok|tx-fails>
  local desc="$1" mode="$2" root="$work/backups" out="$work/job.out" why="" rc
  [ -z "${FC_ONLY:-}" ] || [[ "[job] $desc" == *"$FC_ONLY"* ]] || return 0
  rm -rf "$root" "$work/pg"; mkdir -p "$root/daily" "$root/restoring" "$work/pg"
  echo dump > "$root/daily/x.dump"
  ln "$root/daily/x.dump" "$root/restoring/killed-pod.dump"
  ln "$root/daily/x.dump" "$root/restoring/other-pod.dump"
  echo 0004_x > "$work/pg/version"; echo 0003_y > "$work/pg/dump_version"
  PATH="$work/pgbin:$PATH" PG_STATE="$work/pg" PG_FAIL_TX="$([ "$mode" = tx-fails ] && echo 1)" \
    BACKUPS_ROOT="$root" DUMP="$root/daily/x.dump" HOSTNAME=own-pod REQUIRE_EMPTY=0 \
    POSTGRES_USER=u POSTGRES_DB=d bash "$here/restore-job.sh" > "$out" 2>&1 && rc=0 || rc=$?
  [ ! -e "$root/restoring/killed-pod.dump" ] || why="leaked pin not removed"
  [ -n "$why" ] || [ ! -e "$root/restoring/other-pod.dump" ] || why="leaked pin not removed (other-pod)"
  [ -n "$why" ] || [ ! -e "$root/restoring/own-pod.dump" ] || why="own pin left behind"
  grep -qx 'alembic_version before restore: 0004_x' "$out" || why="${why:-no before line}"
  if [ "$mode" = ok ]; then
    [ -n "$why" ] || [ "$rc" = 0 ] || why="exited $rc"
    grep -qx 'alembic_version after restore: 0003_y' "$out" || why="${why:-no after line}"
  else
    [ -n "$why" ] || [ "$rc" != 0 ] || why="exited 0"
    if grep -q 'restore committed' "$out"; then why="${why:-logged a commit}"; fi
    grep -qx 'alembic_version after failed restore: 0004_x' "$out" || why="${why:-no after-failed line}"
  fi
  if [ -n "$why" ]; then
    echo "FAIL [job] $desc: $why"; sed 's/^/    /' "$out"; failures=$((failures + 1))
  else
    echo "ok   [job] $desc: rc=$rc"
  fi
}
run_job_case "every pin but its own removed (0048 #1)" ok
run_job_case "failed transaction logs the version after the failure (N-3)" tx-fails

if [ "$failures" -ne 0 ]; then
  echo "$failures fail-closed case(s) FAILED" >&2
  exit 1
fi
echo "fail-closed checks passed"
