#!/usr/bin/env bash
# Restore a pg_dump -Fc file from the backup PVC over the live database. Overwrites data, so it
# runs only with CONFIRM=<namespace>. All-or-nothing: the schema drop and the whole restore run
# in ONE psql transaction with ON_ERROR_STOP, so a failure leaves the database as it was.
# Dropping the schema first means objects created by a bad migration do not survive a rollback.
#
# Usage: CONFIRM=<namespace> deployment/k8s/restore.sh <uat|prod> </backups/...dump> [--require-empty]
#   --require-empty  refuse unless the projects table is empty or absent (first cutover only)
set -euo pipefail

env_name="${1:?usage: restore.sh <uat|prod> <dump-path> [--require-empty]}"
dump="${2:?dump path on the backup PVC required, e.g. /backups/pre-migration/<sha>-<ts>.dump}"
require_empty=0
[ "${3:-}" = --require-empty ] && require_empty=1
timeout="${RESTORE_TIMEOUT_SECONDS:-600}"

case "$env_name" in
  uat) ns=issue-tracker-uat ;;
  prod) ns=issue-tracker ;;
  *) echo "unknown environment: $env_name" >&2; exit 2 ;;
esac
[[ "$dump" =~ ^/backups/[A-Za-z0-9._/-]+\.dump$ && "$dump" != *..* ]] || { echo "bad dump path: $dump" >&2; exit 2; }
[ "${CONFIRM:-}" = "$ns" ] || { echo "refusing: set CONFIRM=$ns to overwrite the $ns database" >&2; exit 2; }
expected_context="${EXPECTED_CONTEXT:-issue-tracker-$env_name}"
context="$(kubectl config current-context)"
[ "$context" = "$expected_context" ] || { echo "refusing: context '$context', expected '$expected_context'" >&2; exit 2; }

for job in issue-tracker-backup-predeploy issue-tracker-migrate; do
  active="$(kubectl -n "$ns" get job "$job" -o jsonpath='{.status.active}' 2> /dev/null || true)"
  [ "${active:-0}" -ge 1 ] && { echo "refusing: job $job is active in $ns" >&2; exit 1; }
done

# Stop the in-cluster writer. stdio MCP clients open their own DB sessions (e.g. via kubectl
# exec or a port-forward); the owner must close those first (documentation/guides/k3s.md).
replicas="$(kubectl -n "$ns" get deployment issue-tracker -o jsonpath='{.spec.replicas}' 2> /dev/null || echo 0)"
[ "${replicas:-0}" -ge 1 ] || replicas=1
kubectl -n "$ns" scale deployment/issue-tracker --replicas=0 2> /dev/null || true
kubectl -n "$ns" wait --for=delete pod -l app.kubernetes.io/component=web --timeout=120s 2> /dev/null || true

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
          image: postgres:16
          envFrom:
            - secretRef:
                name: issue-tracker-db
          env:
            - {name: PGHOST, value: issue-tracker-postgres}
            - name: PGPASSWORD
              valueFrom: {secretKeyRef: {name: issue-tracker-db, key: POSTGRES_PASSWORD}}
            - {name: DUMP, value: "$dump"}
            - {name: REQUIRE_EMPTY, value: "$require_empty"}
          command:
            - bash
            - -euo
            - pipefail
            - -c
            - |
              pg_restore -l "\$DUMP" > /dev/null
              echo "dump readable: \$DUMP (\$(pg_restore -l "\$DUMP" | grep -c ' TABLE DATA ') tables with data)"
              {
                echo 'BEGIN;'
                echo 'SET LOCAL client_min_messages = warning;'
                if [ "\$REQUIRE_EMPTY" = 1 ]; then
                  echo "DO \\\$g\\\$ BEGIN IF to_regclass('public.projects') IS NOT NULL AND EXISTS (SELECT 1 FROM public.projects) THEN RAISE EXCEPTION 'projects is not empty; refusing to overwrite'; END IF; END \\\$g\\\$;"
                fi
                echo 'DROP SCHEMA public CASCADE;'
                echo 'CREATE SCHEMA public;'
                pg_restore --no-owner --no-privileges -f - "\$DUMP"
                echo 'COMMIT;'
              } | psql -X -q -v ON_ERROR_STOP=1 -U "\$POSTGRES_USER" -d "\$POSTGRES_DB" > /dev/null
              psql -X -At -U "\$POSTGRES_USER" -d "\$POSTGRES_DB" -c 'select version_num from alembic_version' \
                | sed 's/^/alembic_version after restore: /' || true
          volumeMounts:
            - {name: backups, mountPath: /backups, readOnly: true}
      volumes:
        - name: backups
          persistentVolumeClaim: {claimName: issue-tracker-backups}
YAML

deadline=$((SECONDS + timeout)) status=""
while (( SECONDS < deadline )); do
  [ -n "$(kubectl -n "$ns" get job "$job" -o jsonpath='{.status.succeeded}')" ] && { status=ok; break; }
  [ -n "$(kubectl -n "$ns" get job "$job" -o jsonpath='{.status.failed}')" ] && { status=failed; break; }
  sleep 3
done
kubectl -n "$ns" logs "job/$job" || true

# The transaction either committed or rolled back, so restarting the app is safe either way.
kubectl -n "$ns" scale deployment/issue-tracker --replicas="$replicas" 2> /dev/null || true
if [ "$status" != ok ]; then
  echo "restore ${status:-timed out}; the database was left unchanged (transaction rolled back)" >&2
  exit 1
fi
kubectl -n "$ns" rollout status deployment/issue-tracker --timeout=300s 2> /dev/null || true
echo "restored $dump into $ns. If alembic_version is behind head, the next pipeline run backs up and migrates it forward."
