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

for job in issue-tracker-backup-predeploy issue-tracker-migrate; do
  active="$(kubectl -n "$ns" get job "$job" -o jsonpath='{.status.active}' 2> /dev/null || true)"
  [ "${active:-0}" -ge 1 ] && { echo "refusing: job $job is active in $ns" >&2; exit 1; }
done
active="$(kubectl -n "$ns" get jobs -l app.kubernetes.io/component=restore -o jsonpath='{range .items[*]}{.status.active}{end}')"
[ -z "$active" ] || { echo "refusing: another restore Job is active in $ns" >&2; exit 1; }

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
replicas="$(kubectl -n "$ns" get deployment issue-tracker --ignore-not-found -o jsonpath='{.spec.replicas}')"
if kubectl -n "$ns" get deployment issue-tracker --ignore-not-found -o name | grep -q .; then
  has_app=1
  [ "${replicas:-0}" -ge 1 ] || replicas=1
  kubectl -n "$ns" scale deployment/issue-tracker --replicas=0
  if ! wait_app_gone 120; then
    echo "restore aborted before touching the database (no safety dump, no restore). The app is" >&2
    echo "scaled to 0 but may still be running. Check: kubectl -n $ns get pods -l app.kubernetes.io/component=web" >&2
    echo "Then retry the restore, or bring the app back: kubectl -n $ns scale deployment/issue-tracker --replicas=$replicas" >&2
    exit 1
  fi
else
  replicas=1
  echo "no issue-tracker Deployment in $ns yet; nothing to stop"
fi

kubectl -n "$ns" create configmap issue-tracker-restore-script --from-file=restore-job.sh="$here/restore-job.sh" \
  --dry-run=client -o yaml | kubectl -n "$ns" apply -f - > /dev/null

job="issue-tracker-restore-$(date -u +%Y%m%d%H%M%S)"
echo "context: $context namespace: $ns dump: $dump require_empty: $require_empty job: $job"
kubectl -n "$ns" apply -f - <<YAML
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
  [ -n "$(kubectl -n "$ns" get job "$job" -o jsonpath='{.status.succeeded}')" ] && { status=ok; break; }
  [ -n "$(kubectl -n "$ns" get job "$job" -o jsonpath='{.status.failed}')" ] && { status=failed; break; }
  sleep 3
done
logs="$(kubectl -n "$ns" logs "job/$job" 2>&1 || true)"
echo "$logs"

if [ -z "$status" ]; then
  # Still running: delete the Job so its pod dies and an uncommitted transaction rolls back.
  # It may have committed in the meantime, so the app stays at 0 until the owner checks.
  kubectl -n "$ns" delete job "$job" --wait=true --cascade=foreground --timeout=120s || true
  echo "restore timed out after ${timeout}s; Job $job deleted; app left at 0 replicas." >&2
  echo "The restore is one transaction, so the database is either unchanged or fully restored." >&2
  echo "Check before scaling up: alembic_version and project count (documentation/guides/k3s.md, Restore)," >&2
  echo "then: kubectl -n $ns scale deployment/issue-tracker --replicas=$replicas" >&2
  exit 1
fi

if [ "$keep_down" = 1 ] && [ "$status" = ok ]; then
  echo "restored $dump into $ns; app left at 0 replicas (--keep-app-down)."
  echo "Next: kubectl -n $ns set image deployment/issue-tracker app=<image that matches this schema>"
  echo "then: kubectl -n $ns scale deployment/issue-tracker --replicas=$replicas"
  exit 0
fi
[ "$has_app" = 1 ] && kubectl -n "$ns" scale deployment/issue-tracker --replicas="$replicas"
if [ "$status" = failed ]; then
  if grep -q '^restore committed$' <<< "$logs"; then
    echo "restore committed but the Job failed afterwards; inspect $job" >&2
  else
    echo "restore failed before COMMIT; the database is unchanged (transaction rolled back)" >&2
  fi
  exit 1
fi
[ "$has_app" = 1 ] && kubectl -n "$ns" rollout status deployment/issue-tracker --timeout=300s
echo "restored $dump into $ns. If alembic_version is behind head, the next pipeline run backs up and migrates it forward."
