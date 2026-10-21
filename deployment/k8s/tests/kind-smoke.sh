#!/usr/bin/env bash
# Disposable-cluster proof for deployment/k8s (CI `k8s` job). Expects a kind cluster in the
# current kubectl context with <image:tag> already loaded. Never point this at a real cluster.
#
# Usage: deployment/k8s/tests/kind-smoke.sh <image:tag> <git-sha>
set -euo pipefail
image="${1:?image:tag}"
sha="${2:?git sha}"
ns=issue-tracker-uat
here="$(cd "$(dirname "$0")/.." && pwd)"

ctx="$(kubectl config current-context)"
[[ "$ctx" == kind-* ]] || { echo "refusing: context '$ctx' is not a kind cluster" >&2; exit 2; }
export EXPECTED_CONTEXT="$ctx"
expect_fail() {  # expect_fail <description> <command...>
  local d="$1"; shift
  if "$@"; then echo "FAIL: expected refusal: $d" >&2; exit 1; fi
  echo "ok: refused: $d"
}
psql_pg() {
  kubectl -n "$ns" exec issue-tracker-postgres-0 -- sh -c "psql -X -At -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -c \"$1\""
}

# k3s names its default class local-path; kind's provisioner is the same rancher local-path one.
kubectl apply -f - <<'YAML'
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: local-path
provisioner: rancher.io/local-path
reclaimPolicy: Delete
volumeBindingMode: WaitForFirstConsumer
YAML

# Owner actions, with throwaway values.
kubectl create namespace "$ns" --dry-run=client -o yaml | kubectl apply -f -
kubectl -n "$ns" create secret generic issue-tracker-db \
  --from-literal=POSTGRES_USER=issue_tracker --from-literal=POSTGRES_DB=issue_tracker \
  --from-literal=POSTGRES_PASSWORD="$(openssl rand -hex 24)" --dry-run=client -o yaml | kubectl apply -f -
kubectl -n "$ns" create secret generic issue-tracker-app \
  --from-literal=APP_SECRET_KEY="$(openssl rand -hex 32)" \
  --from-literal=ADMIN_INITIAL_PASSWORD=ci-e2e-password --dry-run=client -o yaml | kubectl apply -f -

echo "== deploy refuses the wrong kubectl context"
expect_fail "context mismatch" env EXPECTED_CONTEXT=issue-tracker-uat "$here/deploy.sh" uat "$image" "$sha"

echo "== first deploy"
"$here/deploy.sh" uat "$image" "$sha"

echo "== redeploy same image (idempotent; Postgres pod and revision must not change)"
pg_uid="$(kubectl -n "$ns" get pod issue-tracker-postgres-0 -o jsonpath='{.metadata.uid}')"
pg_rev="$(kubectl -n "$ns" get statefulset issue-tracker-postgres -o jsonpath='{.status.currentRevision}')"
"$here/deploy.sh" uat "$image" "$sha"
[ "$(kubectl -n "$ns" get pod issue-tracker-postgres-0 -o jsonpath='{.metadata.uid}')" = "$pg_uid" ] \
  || { echo "Postgres pod was replaced by a no-op redeploy" >&2; exit 1; }
sts="$(kubectl -n "$ns" get statefulset issue-tracker-postgres -o jsonpath='{.status.currentRevision} {.status.updateRevision}')"
[ "$sts" = "$pg_rev $pg_rev" ] || { echo "StatefulSet revision changed: $pg_rev -> $sts" >&2; exit 1; }
echo "ok: Postgres pod $pg_uid and revision $pg_rev unchanged"

echo "== migration refuses to run without the backup deploy.sh named"
kubectl -n "$ns" delete job issue-tracker-migrate --wait=true
tmp="$(mktemp -d "$here/.render.XXXXXX")"; trap 'rm -rf "$tmp"' EXIT
kubectl kustomize "$here/overlays/uat/jobs" \
  | kubectl set env --local -f - BACKUP_FILE=/backups/pre-migration/missing.dump -o yaml > "$tmp/jobs.yaml"
kubectl -n "$ns" apply -f "$tmp/jobs.yaml" -l app.kubernetes.io/component=migrate
for _ in $(seq 1 60); do
  failed="$(kubectl -n "$ns" get job issue-tracker-migrate -o jsonpath='{.status.failed}')"
  [ "${failed:-0}" -ge 1 ] && break
  sleep 3
done
[ "${failed:-0}" -ge 1 ] || { echo "migrate Job without backup did not fail" >&2; exit 1; }
kubectl -n "$ns" logs job/issue-tracker-migrate -c require-backup | grep -q "refusing to migrate"
[ -z "$(kubectl -n "$ns" get job issue-tracker-migrate -o jsonpath='{.status.succeeded}')" ]
echo "ok: migrate Job refused without backup"
kubectl -n "$ns" delete job issue-tracker-migrate --wait=true

echo "== deploy refuses while a migrate Job is active"
kubectl -n "$ns" create job issue-tracker-migrate --image=postgres:16 -- sleep 300
kubectl -n "$ns" wait --for=jsonpath='{.status.active}'=1 job/issue-tracker-migrate --timeout=120s
expect_fail "active migrate Job" "$here/deploy.sh" uat "$image" "$sha"
kubectl -n "$ns" delete job issue-tracker-migrate --wait=true

echo "== backup CronJob prunes to 14 daily + 5 pre-migration"
kubectl -n "$ns" apply -f - <<'YAML'
apiVersion: batch/v1
kind: Job
metadata:
  name: seed-old-backups
spec:
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: seed
          image: postgres:16
          command:
            - sh
            - -euc
            - |
              mkdir -p /backups/daily /backups/pre-migration
              for i in $(seq 1 20); do
                f="/backups/daily/old-$i.dump"; echo x > "$f"; touch -d "@$(( $(date +%s) - 86400 * (i + 1) ))" "$f"
              done
              for i in $(seq 1 8); do
                f="/backups/pre-migration/old-$i.dump"; echo x > "$f"; touch -d "@$(( $(date +%s) - 86400 * (i + 30) ))" "$f"
              done
          volumeMounts:
            - name: backups
              mountPath: /backups
      volumes:
        - name: backups
          persistentVolumeClaim:
            claimName: issue-tracker-backups
YAML
kubectl -n "$ns" wait --for=condition=complete job/seed-old-backups --timeout=180s
kubectl -n "$ns" create job backup-now --from=cronjob/issue-tracker-backup-daily
kubectl -n "$ns" wait --for=condition=complete job/backup-now --timeout=180s
out="$(kubectl -n "$ns" logs job/backup-now)"
echo "$out"
kubectl -n "$ns" apply -f - <<'YAML'
apiVersion: batch/v1
kind: Job
metadata:
  name: count-backups
spec:
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: count
          image: postgres:16
          command:
            - sh
            - -euc
            - |
              d=$(ls /backups/daily/*.dump | wc -l); p=$(ls /backups/pre-migration/*.dump | wc -l)
              echo "daily=$d pre-migration=$p"; ls -lt /backups/daily /backups/pre-migration
              test "$d" -eq 14 && test "$p" -eq 5
              # The two real pre-migration dumps from the deploys above must survive the prune.
              test "$(ls /backups/pre-migration/ | grep -vc '^old-')" -eq 2
          volumeMounts:
            - name: backups
              mountPath: /backups
              readOnly: true
      volumes:
        - name: backups
          persistentVolumeClaim:
            claimName: issue-tracker-backups
YAML
kubectl -n "$ns" wait --for=condition=complete job/count-backups --timeout=180s
kubectl -n "$ns" logs job/count-backups | head -1

echo "== storage"
kubectl get pvc -n "$ns" -o custom-columns=NAME:.metadata.name,REQUEST:.spec.resources.requests.storage,CLASS:.spec.storageClassName,STATUS:.status.phase

echo "== browser workflow suite"
"$here/e2e.sh" "$ns"
shots="$(find "${E2E_OUT:-artifacts/e2e-k8s}" -name '*.png' 2> /dev/null | wc -l)"
[ "$shots" -gt 0 ] || { echo "e2e produced no screenshots" >&2; exit 1; }
projects="$(psql_pg 'select count(*) from projects')"
echo "projects after e2e: $projects"
[ "$projects" -gt 0 ]

echo "== backup files: off-cluster copy and upload round trip"
off="$(mktemp -d)"
"$here/backup-files.sh" uat list
"$here/backup-files.sh" uat get-latest "$off"
ls -l "$off"
daily="$off/$(ls "$off" | grep -E '^[0-9]{8}T[0-9]{6}Z\.dump$' | head -1)"
[ -s "$daily" ] || { echo "no daily dump copied off-cluster" >&2; exit 1; }
"$here/backup-files.sh" uat put "$daily" roundtrip.dump

echo "== restore guards"
expect_fail "restore without CONFIRM" "$here/restore.sh" uat /backups/imports/roundtrip.dump
expect_fail "--require-empty on a database with projects" \
  env CONFIRM="$ns" "$here/restore.sh" uat /backups/imports/roundtrip.dump --require-empty
[ "$(psql_pg 'select count(*) from projects')" = "$projects" ] || { echo "refused restore changed data" >&2; exit 1; }
echo "ok: refused restore left $projects projects in place"

echo "== restore (rollback path): drop schema + restore the pre-e2e daily dump in one transaction"
psql_pg 'create table leftover_from_bad_migration (id int)' > /dev/null
CONFIRM="$ns" "$here/restore.sh" uat /backups/imports/roundtrip.dump
[ "$(psql_pg "select count(*) from information_schema.tables where table_name = 'leftover_from_bad_migration'")" = 0 ] \
  || { echo "object from the bad migration survived the restore" >&2; exit 1; }
restored="$(psql_pg 'select count(*) from projects')"
[ "$restored" -lt "$projects" ] || { echo "restore did not roll data back ($restored vs $projects)" >&2; exit 1; }
echo "ok: restored to $restored projects (was $projects); leftover table gone"
kubectl -n "$ns" rollout status deployment/issue-tracker --timeout=300s
kubectl -n "$ns" exec deploy/issue-tracker -c app -- python -c \
  "import json,urllib.request; d=json.load(urllib.request.urlopen('http://127.0.0.1:8000/health')); assert d['database'] == 'ok', d; print(d)"
echo "kind smoke passed"
