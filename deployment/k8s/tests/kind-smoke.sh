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
pvc_sh() {  # pvc_sh <job-name> <script>: run a one-off script against the backup PVC
  kubectl -n "$ns" apply -f - > /dev/null <<YAML
apiVersion: batch/v1
kind: Job
metadata: {name: $1}
spec:
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: sh
          image: postgres:16.15
          command: ["sh", "-euc", $(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$2")]
          volumeMounts: [{name: backups, mountPath: /backups}]
      volumes: [{name: backups, persistentVolumeClaim: {claimName: issue-tracker-backups}}]
YAML
  kubectl -n "$ns" wait --for=condition=complete "job/$1" --timeout=180s > /dev/null
  kubectl -n "$ns" delete job "$1" --wait=true > /dev/null
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
owner_setup() {
  kubectl create namespace "$ns" --dry-run=client -o yaml | kubectl apply -f -
  kubectl -n "$ns" create secret generic issue-tracker-db \
    --from-literal=POSTGRES_USER=issue_tracker --from-literal=POSTGRES_DB=issue_tracker \
    --from-literal=POSTGRES_PASSWORD="$(openssl rand -hex 24)" --dry-run=client -o yaml | kubectl apply -f -
  kubectl -n "$ns" create secret generic issue-tracker-app \
    --from-literal=APP_SECRET_KEY="$(openssl rand -hex 32)" \
    --from-literal=ADMIN_INITIAL_PASSWORD=ci-e2e-password --dry-run=client -o yaml | kubectl apply -f -
}
owner_setup

echo "== deploy refuses the wrong kubectl context"
expect_fail "context mismatch" env EXPECTED_CONTEXT=issue-tracker-uat "$here/deploy.sh" uat "$image" "$sha"

echo "== first deploy"
"$here/deploy.sh" uat "$image" "$sha"

echo "== redeploy same image (idempotent; Postgres pod and revision must not change)"
pg_uid="$(kubectl -n "$ns" get pod issue-tracker-postgres-0 -o jsonpath='{.metadata.uid}')"
pg_rev="$(kubectl -n "$ns" get statefulset issue-tracker-postgres -o jsonpath='{.status.currentRevision}')"
app_pod="$(kubectl -n "$ns" get pod -l app.kubernetes.io/component=web -o jsonpath='{.items[0].metadata.uid}')"
deploy_log="$(mktemp)"
"$here/deploy.sh" uat "$image" "$sha" | tee "$deploy_log"
# Maintenance window: the app was stopped for backup + migrate, so its pod is a new one.
grep -q '^maintenance: app scaled to 0 for backup + migrate$' "$deploy_log"
[ "$(kubectl -n "$ns" get pod -l app.kubernetes.io/component=web -o jsonpath='{.items[0].metadata.uid}')" != "$app_pod" ] \
  || { echo "app pod survived the maintenance window" >&2; exit 1; }
echo "ok: app was scaled to 0 for backup + migrate and came back"
head_dump="$(grep -o '/backups/pre-migration/[^ ]*\.dump' "$deploy_log" | sed -n 1p)"
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
kubectl -n "$ns" create job issue-tracker-migrate --image=postgres:16.15 -- sleep 300
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
          image: postgres:16.15
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
          image: postgres:16.15
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
kubectl -n "$ns" logs job/count-backups | sed -n 1p

echo "== migrate Job outlives its timeout: Job deleted, app stays at 0 when the version is unknowable (B1)"
# Simulates an ALTER waiting on a lock held by another session (e.g. a stdio MCP client): once
# the backup has finished, hold ACCESS EXCLUSIVE on alembic_version so the migration blocks.
# The same lock makes alembic_version unreadable, so deploy.sh must not bring the old app back.
version="$(psql_pg 'select version_num from alembic_version')"
kubectl -n "$ns" delete job issue-tracker-backup-predeploy --ignore-not-found --wait=true
(
  until [ "$(kubectl -n "$ns" get job issue-tracker-backup-predeploy -o jsonpath='{.status.succeeded}' 2> /dev/null)" = 1 ]; do
    sleep 0.5
  done
  kubectl -n "$ns" exec issue-tracker-postgres-0 -c postgres -- sh -c \
    'psql -X -q -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "BEGIN; LOCK TABLE alembic_version IN ACCESS EXCLUSIVE MODE; SELECT pg_sleep(900);"'
) > /dev/null 2>&1 &
locker=$!
b1_log="$(mktemp)"
if DEPLOY_TIMEOUT_SECONDS=60 "$here/deploy.sh" uat "$image" "$sha" > "$b1_log" 2>&1; then
  cat "$b1_log"; echo "deploy succeeded although the migration was blocked" >&2; exit 1
fi
cat "$b1_log"
grep -q '^deploy failed during: migrate$' "$b1_log"
grep -q '^LEAVING THE APP AT 0' "$b1_log"
[ -z "$(kubectl -n "$ns" get job issue-tracker-migrate --ignore-not-found -o name)" ] || { echo "migrate Job survived" >&2; exit 1; }
[ "$(kubectl -n "$ns" get deployment issue-tracker -o jsonpath='{.spec.replicas}')" = 0 ] \
  || { echo "old app came back while alembic_version was unknowable" >&2; exit 1; }
psql_pg "select pg_terminate_backend(pid) from pg_stat_activity where query like '%pg_sleep(900)%' and pid <> pg_backend_pid()" > /dev/null
kill "$locker" 2> /dev/null || true
wait "$locker" 2> /dev/null || true
# The owner's check from the message: version unchanged, so scaling the old app up is safe.
[ "$(psql_pg 'select version_num from alembic_version')" = "$version" ]
kubectl -n "$ns" scale deployment/issue-tracker --replicas=1
kubectl -n "$ns" rollout status deployment/issue-tracker --timeout=300s
echo "ok: blocked migration -> Job deleted, app left at 0, alembic_version still $version"

echo "== backup fails: migrate never runs, old app back with a clear message (B1)"
pvc_sh break-backups 'mv /backups/pre-migration /backups/pre-migration.saved && touch /backups/pre-migration'
b2_log="$(mktemp)"
if "$here/deploy.sh" uat "$image" "$sha" > "$b2_log" 2>&1; then
  cat "$b2_log"; echo "deploy succeeded although the backup failed" >&2; exit 1
fi
cat "$b2_log"
grep -q '^deploy failed during: backup$' "$b2_log"
grep -q 'Jobs deleted and alembic_version unchanged.*restoring the previous app' "$b2_log"
! grep -q 'job.batch/issue-tracker-migrate created' "$b2_log" || { echo "migrate ran after a failed backup" >&2; exit 1; }
kubectl -n "$ns" rollout status deployment/issue-tracker --timeout=300s
pvc_sh fix-backups 'rm /backups/pre-migration && mv /backups/pre-migration.saved /backups/pre-migration'
echo "ok: failed backup -> no migration, old app back"

echo "== migrate Job times out, Jobs deleted, version unchanged -> old app back (NB5)"
# A memory quota that admits the backup pod (Postgres 256Mi + backup 64Mi) but not the migrate
# pod (+128Mi), so the migration never starts and times out. alembic_version stays readable.
version="$(psql_pg 'select version_num from alembic_version')"
kubectl -n "$ns" apply -f - <<'YAML'
apiVersion: v1
kind: ResourceQuota
metadata: {name: block-migrate}
spec:
  hard: {requests.memory: 320Mi}
YAML
for _ in $(seq 1 60); do
  [ -n "$(kubectl -n "$ns" get resourcequota block-migrate -o jsonpath='{.status.used.requests\.memory}')" ] && break
  sleep 1
done
nb5_log="$(mktemp)"
if DEPLOY_TIMEOUT_SECONDS=60 "$here/deploy.sh" uat "$image" "$sha" > "$nb5_log" 2>&1; then
  cat "$nb5_log"; kubectl -n "$ns" delete resourcequota block-migrate
  echo "deploy succeeded although the migrate pod was blocked" >&2; exit 1
fi
cat "$nb5_log"
kubectl -n "$ns" delete resourcequota block-migrate
grep -q '^deploy failed during: migrate$' "$nb5_log"
grep -q "job issue-tracker-backup-predeploy complete" "$nb5_log"
grep -q 'Jobs deleted and alembic_version unchanged.*restoring the previous app (replicas=1)' "$nb5_log"
[ -z "$(kubectl -n "$ns" get job issue-tracker-migrate --ignore-not-found -o name)" ] || { echo "migrate Job survived" >&2; exit 1; }
[ "$(kubectl -n "$ns" get deployment issue-tracker -o jsonpath='{.spec.replicas}')" = 1 ]
kubectl -n "$ns" rollout status deployment/issue-tracker --timeout=300s
[ "$(psql_pg 'select version_num from alembic_version')" = "$version" ]
echo "ok: migrate timed out -> Jobs deleted, alembic_version still $version, old app scaled back up"

echo "== restore aborts before the safety dump when the app can't be stopped (NB1)"
# An app pod that ignores deletion: a finalizer keeps it Terminating past the 120s wait.
app_pod="$(kubectl -n "$ns" get pod -l app.kubernetes.io/component=web -o jsonpath='{.items[0].metadata.name}')"
kubectl -n "$ns" patch pod "$app_pod" --type=merge -p '{"metadata":{"finalizers":["example.com/hold"]}}'
safety_before="$(kubectl -n "$ns" get jobs -l app.kubernetes.io/component=restore -o name | wc -l)"
expect_fail "restore while the app pod won't stop" env CONFIRM="$ns" "$here/restore.sh" uat "$head_dump"
[ "$(kubectl -n "$ns" get jobs -l app.kubernetes.io/component=restore -o name | wc -l)" = "$safety_before" ] \
  || { echo "restore Job started although the app did not stop" >&2; exit 1; }
kubectl -n "$ns" patch pod "$app_pod" --type=merge -p '{"metadata":{"finalizers":null}}'
kubectl -n "$ns" wait --for=delete "pod/$app_pod" --timeout=120s
kubectl -n "$ns" scale deployment/issue-tracker --replicas=1
kubectl -n "$ns" rollout status deployment/issue-tracker --timeout=300s
echo "ok: restore aborted before any restore Job when the app pod would not stop"

echo "== storage"
kubectl get pvc -n "$ns" -o custom-columns=NAME:.metadata.name,REQUEST:.spec.resources.requests.storage,CLASS:.spec.storageClassName,STATUS:.status.phase

echo "== restore --require-empty passes on an EMPTY projects table (NB2)"
[ "$(psql_pg 'select count(*) from projects')" = 0 ]
CONFIRM="$ns" "$here/restore.sh" uat "$head_dump" --require-empty
echo "ok: --require-empty passed with an empty projects table"
# 0042 N3: alembic_version was the same before and after, so the app is back at its previous 1.
[ "$(kubectl -n "$ns" get deployment issue-tracker -o jsonpath='{.spec.replicas}')" = 1 ] \
  || { echo "same-revision restore did not bring the app back to 1 replica" >&2; exit 1; }
kubectl -n "$ns" rollout status deployment/issue-tracker --timeout=300s
echo "ok: same-revision restore brought the app back to 1 replica"

echo "== restore lock: refused while held, left in place (0047 N-1)"
kubectl -n "$ns" create configmap issue-tracker-restore-lock --from-literal=job=held-by-test
expect_fail "restore while the restore lock is held" env CONFIRM="$ns" "$here/restore.sh" uat "$head_dump"
[ -n "$(kubectl -n "$ns" get configmap issue-tracker-restore-lock --ignore-not-found -o name)" ] \
  || { echo "a refused restore released a lock it didn't hold" >&2; exit 1; }
[ "$(kubectl -n "$ns" get deployment issue-tracker -o jsonpath='{.spec.replicas}')" = 1 ] \
  || { echo "a refused restore touched the app" >&2; exit 1; }
kubectl -n "$ns" delete configmap issue-tracker-restore-lock
echo "ok: restore refused while the lock was held; lock and app untouched"

echo "== restore that changes alembic_version leaves the app at 0; leaked pin cleared (0042 N1, N2; 0047 N-2)"
# A pin leaked by a SIGKILLed restore Job (bash as PID 1 ignores SIGTERM, so its EXIT trap never ran),
# and the pin of a restore pod that is still running (a bare pod, so no restore Job is active).
pvc_sh plant-stale-pin "mkdir -p /backups/restoring && ln $head_dump /backups/restoring/killed-pod.dump && ln $head_dump /backups/restoring/fake-running-restore.dump"
kubectl -n "$ns" run fake-running-restore --image=postgres:16.15 --restart=Never \
  --labels=app.kubernetes.io/name=issue-tracker,app.kubernetes.io/component=restore -- sleep 600
kubectl -n "$ns" wait --for=condition=Ready pod/fake-running-restore --timeout=180s
# The live schema reads as another revision than the dump's, as after a deploy migrated past it.
psql_pg "update alembic_version set version_num = '0003_fake_other'" > /dev/null
n1_log="$(mktemp)"
if CONFIRM="$ns" "$here/restore.sh" uat "$head_dump" > "$n1_log" 2>&1; then
  cat "$n1_log"; echo "a restore across revisions exited 0" >&2; exit 1
fi
cat "$n1_log"
grep -q "alembic_version went from '0003_fake_other' to '" "$n1_log"
grep -q "removed '/backups/restoring/killed-pod.dump'" "$n1_log"
grep -q "keeping pin of running restore pod fake-running-restore" "$n1_log"
[ -z "$(kubectl -n "$ns" get configmap issue-tracker-restore-lock --ignore-not-found -o name)" ] \
  || { echo "restore did not release its lock" >&2; exit 1; }
[ "$(kubectl -n "$ns" get deployment issue-tracker -o jsonpath='{.spec.replicas}')" = 0 ] \
  || { echo "restore across revisions scaled the app up" >&2; exit 1; }
[ "$(psql_pg 'select version_num from alembic_version')" != 0003_fake_other ]
pvc_sh check-pins '[ "$(ls -A /backups/restoring)" = fake-running-restore.dump ] && rm /backups/restoring/fake-running-restore.dump'
kubectl -n "$ns" delete pod fake-running-restore --wait=true
echo "ok: app left at 0 after a restore that changed alembic_version; leaked pin removed, running pod's pin kept, lock released"

echo "== restore --require-empty passes when projects is ABSENT (NB2)"
kubectl -n "$ns" scale deployment/issue-tracker --replicas=0
kubectl -n "$ns" wait --for=delete pod -l app.kubernetes.io/component=web --timeout=120s || true
psql_pg 'drop schema public cascade; create schema public' > /dev/null
[ -z "$(psql_pg "select to_regclass('public.projects')")" ]
CONFIRM="$ns" "$here/restore.sh" uat "$head_dump" --require-empty
[ -n "$(psql_pg 'select version_num from alembic_version')" ]
echo "ok: --require-empty passed with no projects table; schema restored at $(psql_pg 'select version_num from alembic_version')"
# The app was at 0 before that restore, so it stays at 0 (B1, round 3); bring it back for e2e.
[ "$(kubectl -n "$ns" get deployment issue-tracker -o jsonpath='{.spec.replicas}')" = 0 ] \
  || { echo "restore scaled up an app that was at 0" >&2; exit 1; }
kubectl -n "$ns" scale deployment/issue-tracker --replicas=1
kubectl -n "$ns" rollout status deployment/issue-tracker --timeout=300s

echo "== every restore wrote a readable safety dump first (NB3)"
"$here/backup-files.sh" uat list | tee "$deploy_log.list"
safety_after="$(awk '/^\/backups\/pre-restore:/{f=1; next} /^$/{f=0} f && /\.dump$/{n++} END{print n+0}' "$deploy_log.list")"
echo "pre-restore dumps: $safety_after"
[ "$safety_after" -ge 2 ] || { echo "expected at least 2 pre-restore safety dumps" >&2; exit 1; }

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
daily="$off/$(ls "$off" | grep -E '^[0-9]{8}T[0-9]{6}Z\.dump$' | sed -n 1p)"
[ -s "$daily" ] || { echo "no daily dump copied off-cluster" >&2; exit 1; }
"$here/backup-files.sh" uat put "$daily" roundtrip.dump

echo "== restore guards"
expect_fail "restore without CONFIRM" "$here/restore.sh" uat /backups/imports/roundtrip.dump
expect_fail "--require-empty on a database with projects" \
  env CONFIRM="$ns" "$here/restore.sh" uat /backups/imports/roundtrip.dump --require-empty
[ "$(psql_pg 'select count(*) from projects')" = "$projects" ] || { echo "refused restore changed data" >&2; exit 1; }
echo "ok: refused restore left $projects projects in place"

echo "== deploy refuses while a restore Job is active (NB3)"
kubectl -n "$ns" create job fake-restore --image=postgres:16.15 -- sleep 300
kubectl -n "$ns" label job fake-restore app.kubernetes.io/component=restore
kubectl -n "$ns" wait --for=jsonpath='{.status.active}'=1 job/fake-restore --timeout=120s
expect_fail "active restore Job" "$here/deploy.sh" uat "$image" "$sha"
expect_fail "second restore while one is active" env CONFIRM="$ns" "$here/restore.sh" uat /backups/imports/roundtrip.dump
kubectl -n "$ns" delete job fake-restore --wait=true

echo "== restore timeout: Job deleted, app left at 0, data unchanged (NB1)"
expect_fail "restore that outlives its timeout" env CONFIRM="$ns" RESTORE_TEST_DELAY_SECONDS=600 \
  RESTORE_TIMEOUT_SECONDS=60 "$here/restore.sh" uat /backups/imports/roundtrip.dump
[ -z "$(kubectl -n "$ns" get jobs -l app.kubernetes.io/component=restore -o jsonpath='{range .items[?(@.status.active)]}{.metadata.name}{end}')" ] \
  || { echo "timed-out restore Job still active" >&2; exit 1; }
[ "$(kubectl -n "$ns" get deployment issue-tracker -o jsonpath='{.spec.replicas}')" = 0 ] \
  || { echo "app was scaled up after a timed-out restore" >&2; exit 1; }
[ "$(psql_pg 'select count(*) from projects')" = "$projects" ] || { echo "timed-out restore changed data" >&2; exit 1; }
[ -z "$(kubectl -n "$ns" get configmap issue-tracker-restore-lock --ignore-not-found -o name)" ] \
  || { echo "timed-out restore kept its lock although its Job was deleted" >&2; exit 1; }
echo "ok: timed-out restore left the app at 0 and $projects projects in place"
kubectl -n "$ns" scale deployment/issue-tracker --replicas=1
kubectl -n "$ns" rollout status deployment/issue-tracker --timeout=300s

echo "== restore (rollback path): drop schema + restore the pre-e2e daily dump in one transaction"
psql_pg 'create table leftover_from_bad_migration (id int)' > /dev/null
CONFIRM="$ns" "$here/restore.sh" uat /backups/imports/roundtrip.dump --keep-app-down
[ "$(kubectl -n "$ns" get deployment issue-tracker -o jsonpath='{.spec.replicas}')" = 0 ] \
  || { echo "--keep-app-down scaled the app up" >&2; exit 1; }
echo "ok: --keep-app-down left the app at 0"
[ "$(psql_pg "select count(*) from information_schema.tables where table_name = 'leftover_from_bad_migration'")" = 0 ] \
  || { echo "object from the bad migration survived the restore" >&2; exit 1; }
restored="$(psql_pg 'select count(*) from projects')"
[ "$restored" -lt "$projects" ] || { echo "restore did not roll data back ($restored vs $projects)" >&2; exit 1; }
echo "ok: restored to $restored projects (was $projects); leftover table gone"
kubectl -n "$ns" scale deployment/issue-tracker --replicas=1
kubectl -n "$ns" rollout status deployment/issue-tracker --timeout=300s
kubectl -n "$ns" exec deploy/issue-tracker -c app -- python -c \
  "import json,urllib.request; d=json.load(urllib.request.urlopen('http://127.0.0.1:8000/health')); assert d['database'] == 'ok', d; print(d)"
echo "== first deploy into a FRESH namespace and volume, 3 times (Postgres init race)"
# On a new volume the image's entrypoint runs a temporary socket-only server before CREATE
# DATABASE; deploy.sh must wait for the real server over TCP instead of racing it.
for i in 1 2 3; do
  kubectl delete namespace "$ns" --wait=true --timeout=300s
  pv_deadline=$((SECONDS + 120))
  until [ -z "$(kubectl get pv -o jsonpath="{range .items[?(@.spec.claimRef.namespace=='$ns')]}{.metadata.name}{end}")" ]; do
    (( SECONDS < pv_deadline )) || { kubectl get pv >&2; echo "old PVs for $ns not released within 120s" >&2; exit 1; }
    sleep 2
  done
  owner_setup
  fresh_log="$(mktemp)"
  "$here/deploy.sh" uat "$image" "$sha" > "$fresh_log" 2>&1 || { cat "$fresh_log"; echo "fresh deploy $i failed" >&2; exit 1; }
  grep -E '^(postgres: accepting connections|alembic_version before deploy|health:)' "$fresh_log"
  grep -q '^alembic_version before deploy: (none)$' "$fresh_log"
  grep -q '"database":"ok"' "$fresh_log"
  echo "ok: fresh deploy $i"
done

echo "kind smoke passed"
