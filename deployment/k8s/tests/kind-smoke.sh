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

echo "== first deploy"
"$here/deploy.sh" uat "$image" "$sha"
echo "== redeploy same image (idempotent; takes a second pre-migration dump)"
"$here/deploy.sh" uat "$image" "$sha"

echo "== migration refuses to run without a backup for its SHA"
kubectl -n "$ns" delete job issue-tracker-migrate --wait=true
tmp="$(mktemp -d "$here/.render.XXXXXX")"; trap 'rm -rf "$tmp"' EXIT
kubectl kustomize "$here/overlays/uat/jobs" \
  | kubectl set env --local -f - DEPLOY_SHA=0000000 -o yaml > "$tmp/jobs.yaml"
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
echo "kind smoke passed"
