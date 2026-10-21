#!/usr/bin/env bash
# Restore a pg_dump -Fc file from the backup PVC over the live database. Overwrites data, so it
# runs only with CONFIRM=<namespace>. The Job (restore-job.sh) first writes a safety dump of the
# current database to /backups/pre-restore/, then runs the schema drop and the whole restore in
# ONE psql transaction with ON_ERROR_STOP: a failure rolls back to the database as it was, and
# objects created by a bad migration do not survive a successful restore.
#
# Usage: CONFIRM=<namespace> deployment/k8s/restore.sh <uat|prod> </backups/...dump> [--require-empty] [--keep-app-down]
#   --require-empty  refuse unless the projects table is absent or empty (first cutover only)
#   --keep-app-down  leave the app at 0 replicas afterwards (rollback: set the old image first)
# Without --keep-app-down the app returns to its previous replica count only if alembic_version is
# the same before and after the restore; a dump at another revision leaves the app at 0.
set -euo pipefail

env_name="${1:?usage: restore.sh <uat|prod> <dump-path> [--require-empty] [--keep-app-down]}"
dump="${2:?dump path on the backup PVC required, e.g. /backups/pre-migration/<sha>-<ts>.dump}"
require_empty=0 keep_down=0
for flag in "${@:3}"; do
  case "$flag" in
    --require-empty) require_empty=1 ;;
    --keep-app-down) keep_down=1 ;;
    *) echo "unknown option: $flag" >&2; exit 2 ;;
  esac
done
timeout="${RESTORE_TIMEOUT_SECONDS:-600}"
test_delay="${RESTORE_TEST_DELAY_SECONDS:-0}"

case "$env_name" in
  uat) ns=issue-tracker-uat ;;
  prod) ns=issue-tracker ;;
  *) echo "unknown environment: $env_name" >&2; exit 2 ;;
esac
[[ "$dump" =~ ^/backups/[A-Za-z0-9._/-]+\.dump$ && "$dump" != *..* ]] || { echo "bad dump path: $dump" >&2; exit 2; }
[[ "$test_delay" =~ ^[0-9]+$ ]] || { echo "bad RESTORE_TEST_DELAY_SECONDS" >&2; exit 2; }
[ "${CONFIRM:-}" = "$ns" ] || { echo "refusing: set CONFIRM=$ns to overwrite the $ns database" >&2; exit 2; }
expected_context="${EXPECTED_CONTEXT:-issue-tracker-$env_name}"
context="$(kubectl config current-context)"
[ "$context" = "$expected_context" ] || { echo "refusing: context '$context', expected '$expected_context'" >&2; exit 2; }
here="$(cd "$(dirname "$0")" && pwd)"

# Any kubectl error here stops the restore (set -e); only a missing Job reads as "not active".
for job in issue-tracker-backup-predeploy issue-tracker-migrate; do
  active="$(kubectl -n "$ns" get job "$job" --ignore-not-found -o jsonpath='{.status.active}')"
  [ "${active:-0}" -ge 1 ] && { echo "refusing: job $job is active in $ns" >&2; exit 1; }
done
active="$(kubectl -n "$ns" get jobs -l app.kubernetes.io/component=restore -o jsonpath='{range .items[*]}{.status.active}{end}')"
[ -z "$active" ] || { echo "refusing: another restore Job is active in $ns" >&2; exit 1; }

# The restore lock: `kubectl create` of a fixed-name ConfigMap is atomic, so two restore.sh runs
# can never both hold it. It is released on exit, except while this run's Job may still be running.
job="issue-tracker-restore-$(date -u +%Y%m%d%H%M%S)"
lock=issue-tracker-restore-lock
if ! kubectl -n "$ns" create configmap "$lock" --from-literal=job="$job" > /dev/null; then
  echo "refusing: could not take the restore lock (ConfigMap $lock in $ns): another restore holds it, or the API failed." >&2
  echo "If no restore is running (kubectl -n $ns get jobs,pods -l app.kubernetes.io/component=restore)," >&2
  echo "a killed restore.sh left it behind: kubectl -n $ns delete configmap $lock" >&2
  exit 1
fi
job_may_run=0
release_lock() {
  if [ "$job_may_run" = 1 ]; then
    echo "restore lock kept: Job $job may still be running. When it has finished or is gone: kubectl -n $ns delete configmap $lock" >&2
  elif ! kubectl -n "$ns" delete configmap "$lock" --ignore-not-found > /dev/null; then
    echo "could not release the restore lock; once no restore is running: kubectl -n $ns delete configmap $lock" >&2
  fi
}
trap release_lock EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# Stop the in-cluster writer. stdio MCP clients open their own DB sessions (e.g. via kubectl
# exec or a port-forward); the owner must close those first (documentation/guides/k3s.md).
# Wait until no app (component=web) pod exists; fail after $1 seconds. Unlike
# `kubectl wait --for=delete -l`, an already-empty selector counts as success. Fails closed:
# if the pod list can't be read, that is an error, never "gone".
wait_app_gone() {
  local deadline=$((SECONDS + $1)) pods
  while :; do
    if ! pods="$(kubectl -n "$ns" get pods -l app.kubernetes.io/component=web -o name --request-timeout=10s)"; then
      echo "could not list app pods in $ns; refusing to assume the app is stopped" >&2
      return 1
    fi
    [ -n "$pods" ] || return 0
    (( SECONDS < deadline )) || { echo "app pod still present after $1s: $pods" >&2; return 1; }
    sleep 2
  done
}

# Only a missing Deployment is tolerated; any other error, or an app pod that won't stop,
# aborts here, before the safety dump and the restore.
has_app=0
# Decides on one read that fails the script on any API error (set -e). With --ignore-not-found a
# missing Deployment prints "" and a present one always prints its replica count (0 or more).
replicas="$(kubectl -n "$ns" get deployment issue-tracker --ignore-not-found -o jsonpath='{.spec.replicas}')"
# prev_replicas is what the app had before this restore; the app only ever returns to that
# (never above it, and never at all with --keep-app-down). advise_replicas is for messages.
prev_replicas="${replicas:-0}"
advise_replicas="$prev_replicas"
[ "$advise_replicas" -ge 1 ] || advise_replicas=1
restore_app_to=0
[ "$keep_down" = 0 ] && restore_app_to="$prev_replicas"
if [ -n "$replicas" ]; then
  has_app=1
  kubectl -n "$ns" scale deployment/issue-tracker --replicas=0
  if ! wait_app_gone 120; then
    echo "restore aborted before touching the database (no safety dump, no restore). The app is" >&2
    echo "scaled to 0 but may still be running. Check: kubectl -n $ns get pods -l app.kubernetes.io/component=web" >&2
    echo "Then retry the restore, or bring the app back: kubectl -n $ns scale deployment/issue-tracker --replicas=$advise_replicas" >&2
    exit 1
  fi
else
  echo "no issue-tracker Deployment in $ns yet; nothing to stop"
fi

kubectl -n "$ns" create configmap issue-tracker-restore-script --from-file=restore-job.sh="$here/restore-job.sh" \
  --dry-run=client -o yaml | kubectl -n "$ns" apply -f - > /dev/null

echo "context: $context namespace: $ns dump: $dump require_empty: $require_empty job: $job"
# The lock stops a second restore.sh. This re-check catches a restore Job made some other way (by
# hand, or by an older restore.sh without the lock). `create` (not apply) fails on an existing Job
# of the same name instead of silently reusing it.
active="$(kubectl -n "$ns" get jobs -l app.kubernetes.io/component=restore -o jsonpath='{range .items[*]}{.status.active}{end}')"
if [ -n "$active" ]; then
  echo "refusing: another restore Job started in $ns while this one was stopping the app; app left at 0." >&2
  echo "Check: kubectl -n $ns get jobs -l app.kubernetes.io/component=restore; then see documentation/guides/k3s.md, Found the app at 0 replicas." >&2
  exit 1
fi
# Pins of restore pods still running (or about to) are kept by the Job's stale-pin cleanup.
keep_pins="$(kubectl -n "$ns" get pods -l app.kubernetes.io/component=restore \
  -o jsonpath='{range .items[*]}{.metadata.name} {.status.phase}{"\n"}{end}' \
  | awk '$1 != "" && $2 != "Succeeded" && $2 != "Failed" {printf "%s ", $1}')"
job_may_run=1
kubectl -n "$ns" create -f - <<YAML
apiVersion: batch/v1
kind: Job
metadata:
  name: $job
  labels:
    app.kubernetes.io/name: issue-tracker
    app.kubernetes.io/component: restore
spec:
  backoffLimit: 0
  ttlSecondsAfterFinished: 604800
  template:
    metadata:
      labels:
        app.kubernetes.io/name: issue-tracker
        app.kubernetes.io/component: restore
    spec:
      restartPolicy: Never
      containers:
        - name: restore
          image: postgres:16.15
          command: ["bash", "/scripts/restore-job.sh"]
          envFrom:
            - secretRef:
                name: issue-tracker-db
          env:
            - {name: PGHOST, value: issue-tracker-postgres}
            - name: PGPASSWORD
              valueFrom: {secretKeyRef: {name: issue-tracker-db, key: POSTGRES_PASSWORD}}
            - {name: DUMP, value: "$dump"}
            - {name: REQUIRE_EMPTY, value: "$require_empty"}
            - {name: RESTORE_TEST_DELAY_SECONDS, value: "$test_delay"}
            - {name: KEEP_PINS, value: "$keep_pins"}
          volumeMounts:
            - {name: backups, mountPath: /backups}
            - {name: scripts, mountPath: /scripts, readOnly: true}
      volumes:
        - name: backups
          persistentVolumeClaim: {claimName: issue-tracker-backups}
        - name: scripts
          configMap: {name: issue-tracker-restore-script}
YAML

deadline=$((SECONDS + timeout)) status=""
while (( SECONDS < deadline )); do
  # A failed read is "unknown, keep waiting"; at the deadline the timeout path keeps the app at 0.
  if st="$(kubectl -n "$ns" get job "$job" -o jsonpath='{.status.succeeded}/{.status.failed}' --request-timeout=10s)"; then
    case "$st" in
      [1-9]*/*) status=ok; break ;;
      */[1-9]*) status=failed; break ;;
    esac
  fi
  sleep 3
done
logs_ok=1
logs="$(kubectl -n "$ns" logs "job/$job" 2>&1)" || logs_ok=0
echo "$logs"
committed=unknown
if [ "$logs_ok" = 1 ]; then
  if grep -q '^restore committed$' <<< "$logs"; then committed=yes; else committed=no; fi
fi
# The value of the log line "<key>: <value>", or "" unless there is exactly one such line.
log_value() {
  [ "$logs_ok" = 1 ] || return 0
  if [ "$(grep -c "^$1: " <<< "$logs" || true)" = 1 ]; then sed -n "s/^$1: //p" <<< "$logs"; fi
}
# Same, real revision (not "(none)", "(empty)" or "(unreadable)") in both lines -> "1".
same_version() { [[ -n "$1" && "$1" = "$2" && "$1" != "("* ]] && echo 1 || echo 0; }
v_before="$(log_value 'alembic_version before restore')"
[ "$status" != ok ] || job_may_run=0
[ "$status" != failed ] || job_may_run=0

if [ -z "$status" ]; then
  # Still running (or unreadable): delete the Job so its pod dies and an uncommitted transaction
  # rolls back. It may have committed in the meantime, so the app stays at 0 until the owner checks.
  if kubectl -n "$ns" delete job "$job" --wait=true --cascade=foreground --timeout=120s; then
    job_may_run=0
    echo "restore timed out after ${timeout}s; Job $job deleted; app left at 0 replicas." >&2
  else
    echo "restore timed out after ${timeout}s and Job $job could NOT be confirmed deleted; app left at 0." >&2
    echo "It may still be running: kubectl -n $ns get job $job; kubectl -n $ns logs job/$job" >&2
  fi
  echo "The restore is one transaction, so the database is either unchanged or fully restored." >&2
  echo "Check before scaling up: alembic_version and project count (documentation/guides/k3s.md, Restore)," >&2
  echo "then: kubectl -n $ns scale deployment/issue-tracker --replicas=$advise_replicas" >&2
  exit 1
fi

if [ "$status" = failed ]; then
  # On failure the Job re-reads alembic_version. The app comes back only if the logs show no COMMIT
  # and exactly one unchanged revision; anything else (a kill between COMMIT and the log line, an
  # unreadable version) leaves it at 0.
  v_failed="$(log_value 'alembic_version after failed restore')"
  if [ "$committed" = no ] && [ "$(same_version "$v_before" "$v_failed")" = 1 ]; then
    # The old state is intact: put the app back exactly as it was (0 stays 0, and
    # --keep-app-down keeps it at 0).
    if [ "$has_app" = 1 ] && [ "$restore_app_to" -ge 1 ]; then
      kubectl -n "$ns" scale deployment/issue-tracker --replicas="$restore_app_to"
      echo "restore failed before COMMIT; the database is unchanged (transaction rolled back); app back to $restore_app_to replica(s)" >&2
    else
      echo "restore failed before COMMIT; the database is unchanged (transaction rolled back); app left at 0" >&2
      [ "$has_app" = 1 ] && echo "To bring it back: kubectl -n $ns scale deployment/issue-tracker --replicas=$advise_replicas" >&2
    fi
  else
    echo "restore Job $job failed; committed=$committed, alembic_version before '${v_before:-unknown}', after the failure '${v_failed:-unknown}'." >&2
    echo "It is not proven that the database is unchanged, so the app is left at 0." >&2
    echo "Check: kubectl -n $ns logs job/$job; alembic_version and project count, then scale up as in" >&2
    echo "documentation/guides/k3s.md, Found the app at 0 replicas." >&2
  fi
  exit 1
fi

# Success. The app's current image only fits the restored data if the schema revision is the one it
# was running on: the Job logs alembic_version before and after. Unreadable or different -> app at 0.
v_after="$(log_value 'alembic_version after restore')"
schema_same="$(same_version "$v_before" "$v_after")"

if [ "$keep_down" = 1 ]; then
  if [ "$has_app" = 1 ]; then
    echo "restored $dump into $ns; app left at 0 replicas (--keep-app-down)."
    echo "Next: kubectl -n $ns set image deployment/issue-tracker app=<image that matches this schema>"
    echo "then: kubectl -n $ns scale deployment/issue-tracker --replicas=$advise_replicas"
    echo "(or run the pipeline: its deploy migrates the data and brings the app up)"
  else
    echo "restored $dump into $ns. There is no app Deployment yet; the next pipeline deploy creates it,"
    echo "migrates the restored data and brings the app up."
  fi
  exit 0
fi
if [ "$has_app" = 1 ] && [ "$restore_app_to" -ge 1 ] && [ "$schema_same" = 1 ]; then
  kubectl -n "$ns" scale deployment/issue-tracker --replicas="$restore_app_to"
  kubectl -n "$ns" rollout status deployment/issue-tracker --timeout=300s
elif [ "$has_app" = 1 ] && [ "$restore_app_to" -ge 1 ]; then
  if [ "$logs_ok" = 1 ]; then
    echo "restored $dump into $ns, and alembic_version went from '${v_before:-unknown}' to '${v_after:-unknown}'." >&2
  else
    echo "restored $dump into $ns, but the Job logs could not be read to compare alembic_version." >&2
  fi
  echo "The app's current image may not match the restored schema, so the app is left at 0 replicas." >&2
  echo "Next (documentation/guides/k3s.md, Rollback): kubectl -n $ns set image deployment/issue-tracker app=<image that matches ${v_after:-the restored revision}>" >&2
  echo "then: kubectl -n $ns scale deployment/issue-tracker --replicas=$restore_app_to" >&2
  echo "(or run the pipeline: its deploy backs up, migrates the restored data to its image's head and brings the app up)" >&2
  exit 1
elif [ "$has_app" = 1 ]; then
  echo "the app was at 0 replicas before this restore; leaving it at 0"
  echo "To bring it back: kubectl -n $ns scale deployment/issue-tracker --replicas=1"
fi
echo "restored $dump into $ns. If alembic_version is behind head, the next pipeline run backs up and migrates it forward."
