# k3s Deployment Guide (UAT And Production)

UAT and production run on the home-lab k3s cluster (issue 0020). Docker Compose stays for local
development only (`local-development.md`).

| Environment | Namespace | Overlay | Default ingress host |
| --- | --- | --- | --- |
| UAT | `issue-tracker-uat` | `deployment/k8s/overlays/uat` | `issue-tracker-uat.home.arpa` |
| **Production** | `issue-tracker` | `deployment/k8s/overlays/prod` | `issue-tracker.home.arpa` |

Images: `ghcr.io/spacemanspiff99/issue-tracker:<git-sha>`, built by `.github/workflows/image.yml`.
Deploys: `.github/workflows/k3s-pipeline.yml` (manual dispatch) on the self-hosted runner
(`self-hosted, issue-tracker, local-dev`), which calls `deployment/k8s/deploy.sh`. No cloud
session ever reaches the cluster.

## Layout

```
deployment/k8s/
  base/                 ConfigMap, Postgres StatefulSet + headless Service + 2Gi PVC,
                        1Gi backup PVC, daily backup CronJob, app Deployment/Service/Ingress
  base/jobs/            pre-deploy backup Job, migration Job (applied by deploy.sh, in order)
  overlays/{uat,prod}/  namespace, storage class, ingress host, APP_BASE_URL
  overlays/*/jobs/      the Jobs for that namespace
  secrets/*.example.yaml  placeholders only; never rendered, never real values
  deploy.sh             the only deploy path (see "What a deploy does")
  e2e.sh                Playwright workflow suite inside the UAT app pod (skips without tests/e2e)
  tests/kind-smoke.sh   disposable kind cluster proof, run by the CI `k8s` job
```

Overlay values and defaults:

| Value | Default | Where to change |
| --- | --- | --- |
| Storage class | `local-path` (k3s built-in) | both `storageClassName` patches in the overlay |
| Ingress host | `issue-tracker-uat.home.arpa` / `issue-tracker.home.arpa` | Ingress + `APP_BASE_URL` patches in the overlay |
| Ingress class | `traefik` (k3s built-in) | `base/ingress.yaml` |
| Postgres resources | requests 100m CPU / 256Mi, limit 512Mi | `base/postgres.yaml` |
| App resources | requests 100m CPU / 192Mi, limit 512Mi | `base/app.yaml` |
| `SESSION_COOKIE_SECURE` | `"false"` (plain-HTTP ingress) | `base/configmap.yaml`; set `"true"` only with TLS on the ingress |

## Storage sizing

| PVC (per namespace) | Request | Notes |
| --- | --- | --- |
| `data-issue-tracker-postgres-0` | 2Gi | WAL capped: `max_wal_size=256MB`, `min_wal_size=64MB`, `wal_keep_size=0` |
| `issue-tracker-backups` | 1Gi | 14 daily dumps + 5 newest pre-migration dumps; older ones pruned |

UAT + production request 6Gi. Multiply by the storage class replica count for raw usage (Longhorn
3 replicas = 18Gi). UAT may use a 1-replica class.

## Owner actions, in order

Run these from a machine with admin access to the cluster (not from a cloud session). Steps 1–8
and 11 are one-time; 9, 10 and 12 are per release.

**1. Runner tools.** On the self-hosted runner (as the runner user `github`): `kubectl` (same minor
as the cluster ±1), `bash`, `curl`, `python3`.

```bash
kubectl version --client && python3 --version && curl --version | head -1
```

**2. Namespaces.**

```bash
kubectl create namespace issue-tracker-uat
kubectl create namespace issue-tracker
```

**3. Least-privilege deploy identity and kubeconfig on the runner.** The runner user is shared
with other repos, so give it a kubeconfig that can only touch these two namespaces:

```bash
for ns in issue-tracker-uat issue-tracker; do
  kubectl -n "$ns" create serviceaccount issue-tracker-deployer
  kubectl -n "$ns" create rolebinding issue-tracker-deployer \
    --clusterrole=admin --serviceaccount="$ns:issue-tracker-deployer"
done
kubectl create clusterrole issue-tracker-ns-reader --verb=get --resource=namespaces
kubectl create clusterrolebinding issue-tracker-ns-reader --clusterrole=issue-tracker-ns-reader \
  --serviceaccount=issue-tracker-uat:issue-tracker-deployer \
  --serviceaccount=issue-tracker:issue-tracker-deployer
TOKEN="$(kubectl -n issue-tracker-uat create token issue-tracker-deployer --duration=8760h)"
SERVER="$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')"
kubectl config view --minify --raw -o jsonpath='{.clusters[0].cluster.certificate-authority-data}' \
  | base64 -d > /tmp/k3s-ca.crt
KCFG=/tmp/issue-tracker-kubeconfig.yaml
kubectl --kubeconfig "$KCFG" config set-cluster k3s --server="$SERVER" \
  --certificate-authority=/tmp/k3s-ca.crt --embed-certs=true
kubectl --kubeconfig "$KCFG" config set-credentials issue-tracker-deployer --token="$TOKEN"
kubectl --kubeconfig "$KCFG" config set-context issue-tracker --cluster=k3s --user=issue-tracker-deployer
kubectl --kubeconfig "$KCFG" config use-context issue-tracker
rm /tmp/k3s-ca.crt
```

Copy `$KCFG` to the runner as `/home/github/.kube/issue-tracker.yaml` (mode `0600`, owner
`github`), delete the local copy, then in GitHub **Settings → Secrets and variables → Actions →
Variables** create `K3S_KUBECONFIG` = `/home/github/.kube/issue-tracker.yaml`. The SA has `admin`
only in the two namespaces, plus read on namespace objects so `deploy.sh` can preflight. Check
from the runner:

```bash
KUBECONFIG=/home/github/.kube/issue-tracker.yaml kubectl -n issue-tracker-uat get pods
KUBECONFIG=/home/github/.kube/issue-tracker.yaml kubectl auth can-i create deployments -n default  # must be "no"
```

The token expires after a year; repeat the `create token` and `set-credentials` lines to rotate it.

**4. GHCR pull secret** (per namespace). Create a GitHub PAT (classic) with only `read:packages`:

```bash
for ns in issue-tracker-uat issue-tracker; do
  kubectl -n "$ns" create secret docker-registry ghcr-pull --docker-server=ghcr.io \
    --docker-username=spacemanspiff99 --docker-password='<PAT with read:packages>'
done
```

**5. App and database Secrets** (per namespace, different values in each). The DB password is
embedded in `DATABASE_URL`, so keep it hex:

```bash
kubectl -n issue-tracker-uat create secret generic issue-tracker-db \
  --from-literal=POSTGRES_USER=issue_tracker --from-literal=POSTGRES_DB=issue_tracker \
  --from-literal=POSTGRES_PASSWORD="$(openssl rand -hex 24)"
kubectl -n issue-tracker-uat create secret generic issue-tracker-app \
  --from-literal=APP_SECRET_KEY="$(openssl rand -hex 32)" \
  --from-literal=ADMIN_INITIAL_PASSWORD='<UAT admin password; the browser suite logs in with it>'

kubectl -n issue-tracker create secret generic issue-tracker-db \
  --from-literal=POSTGRES_USER=issue_tracker --from-literal=POSTGRES_DB=issue_tracker \
  --from-literal=POSTGRES_PASSWORD="$(openssl rand -hex 24)"
kubectl -n issue-tracker create secret generic issue-tracker-app \
  --from-literal=APP_SECRET_KEY="$(openssl rand -hex 32)" \
  --from-literal=ADMIN_INITIAL_PASSWORD=
```

Never commit these values; `deployment/k8s/secrets/*.example.yaml` shows the shape only. The
Postgres password is fixed at first `initdb`: changing the Secret later does not change the
database role, so rotate with `ALTER ROLE` first, then the Secret, then `kubectl rollout restart`.

**6. Storage class.** List classes and confirm the default:

```bash
kubectl get storageclass
```

`local-path` needs no change. For Longhorn (or another class), edit both `storageClassName`
values in each overlay before the first deploy (a StatefulSet volume claim template cannot be
changed afterwards). For a 1-replica UAT class:

```bash
kubectl apply -f - <<'YAML'
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: longhorn-1r
provisioner: driver.longhorn.io
allowVolumeExpansion: true
parameters:
  numberOfReplicas: "1"
YAML
```

**7. DNS and ingress.** Point `issue-tracker-uat.home.arpa` and `issue-tracker.home.arpa` (or the
hosts you set in the overlays) at the k3s node(s) running Traefik, in the home-lab DNS or the
runner's `/etc/hosts`. Check from the runner after the first deploy:
`curl -fsS http://issue-tracker-uat.home.arpa/health`.

**8. GitHub environments.** `uat` already exists. Make sure `prod` has a required reviewer
(**Settings → Environments → prod**); every production deploy waits for that approval.

**9. Deploy UAT.** Actions → **k3s UAT Production Pipeline** → Run workflow on `main` with
`promote_prod: false`. Check the run log for: image pushed, backup Job wrote
`/backups/pre-migration/<sha>-<ts>.dump`, migrate Job complete, rollout complete,
`health: {"ok": true, "database": "ok"}` in-pod and via ingress, browser suite result.

**10. First production deploy.** Re-run the pipeline on the same commit with `promote_prod: true`.
`Deploy PRODUCTION (k3s)` runs only after `Deploy UAT (k3s)` succeeded in the same run, refuses if
its SHA differs from UAT's, waits for the `prod` reviewer, and runs the same backup → migrate →
rollout → `/health` sequence. The first run creates Postgres and an empty schema at head.

**11. Move production data off Compose (once).** The Compose production at `192.168.10.8` holds
the real data. Stop writes there and dump it (keep the dump outside git):

```bash
# On 192.168.10.8 in /home/akun/issue-tracker/current
docker compose -f deployment/docker-compose.local.yml stop app
docker compose -f deployment/docker-compose.local.yml exec -T postgres \
  pg_dump -U issue_tracker -d issue_tracker -Fc > /home/akun/issue-tracker/backups/to-k3s.dump
```

Copy `to-k3s.dump` onto the production backup PVC (see "Backup and restore"). The k3s production
database is brand new and empty at this point, so restore into a clean schema rather than with
`--clean` (the Compose database may be at an older migration head):

```bash
NS=issue-tracker
kubectl -n "$NS" scale deployment/issue-tracker --replicas=0
# Only on the fresh, never-used k3s production database. Confirm it has no projects first:
kubectl -n "$NS" exec issue-tracker-postgres-0 -- sh -c \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "select count(*) from projects"'
kubectl -n "$NS" exec issue-tracker-postgres-0 -- sh -c \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "drop schema public cascade; create schema public"'
```

Then run the restore Job below with `DUMP=/backups/to-k3s.dump` and `pg_restore` options
`--no-owner` only (drop `--clean --if-exists`), and re-run the pipeline with `promote_prod: true`:
it backs up the restored data and migrates it forward to head. Check projects and issues in the
UI, then switch DNS/bookmarks. Leave the Compose stack stopped, not removed, until you are
satisfied.

**12. Every later release:** steps 9 then 10 (one run with `promote_prod: true` does both).

## What a deploy does (`deploy.sh <uat|prod> <image:tag> <sha>`)

1. Preflight: namespace and `issue-tracker-db` / `issue-tracker-app` Secrets exist (it never creates
   them); warns if `ghcr-pull` is missing.
2. Applies everything except the app (ConfigMap, Postgres, PVCs, CronJob); waits for Postgres.
3. Replaces and runs `issue-tracker-backup-predeploy`: `pg_dump -Fc` to
   `/backups/pre-migration/<sha>-<ts>.dump`, verified with `pg_restore -l`, keeps the newest 5.
4. Runs `issue-tracker-migrate`: an init container refuses unless a valid dump for this SHA exists,
   then `alembic upgrade head`. No flag skips the backup; nothing runs `alembic downgrade`.
5. Applies the app Deployment/Service/Ingress and waits for rollout. The container never migrates
   on start. Readiness requires `/health` to return `"database": "ok"`; liveness is `/health`.
6. Checks `/health` from inside the pod; the pipeline also checks the ingress URL.

The daily CronJob (`03:17` UTC) writes `/backups/daily/<ts>.dump`, keeps 14 daily and 5
pre-migration dumps, and prints `df -h /backups`.

## Storage checks

```bash
kubectl get pvc -A | grep issue-tracker
kubectl -n issue-tracker exec issue-tracker-postgres-0 -- df -h /var/lib/postgresql/data
kubectl -n issue-tracker exec issue-tracker-postgres-0 -- \
  sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "select pg_size_pretty(pg_database_size(current_database()))"'
kubectl -n issue-tracker logs job/$(kubectl -n issue-tracker get jobs -o name | grep backup-daily | tail -1 | cut -d/ -f2) | tail -3
```

Longhorn: the Longhorn UI → Volumes shows actual vs. requested size. `local-path`: `df -h
/var/lib/rancher/k3s/storage` on the node.

## Resizing a PVC

Only classes with `allowVolumeExpansion: true` (Longhorn: yes; `local-path`: no, its size is not
enforced and it grows until the node disk fills).

```bash
kubectl get storageclass <class> -o jsonpath='{.allowVolumeExpansion}'
kubectl -n issue-tracker patch pvc data-issue-tracker-postgres-0 \
  -p '{"spec":{"resources":{"requests":{"storage":"4Gi"}}}}'
kubectl -n issue-tracker patch pvc issue-tracker-backups \
  -p '{"spec":{"resources":{"requests":{"storage":"2Gi"}}}}'
kubectl -n issue-tracker get pvc -w
```

Then update the request in `base/` so a fresh install matches. The StatefulSet's volume claim
template is immutable: changing it in git does not resize the existing PVC, and applying it
fails until you `kubectl -n <ns> delete statefulset issue-tracker-postgres --cascade=orphan` (keeps
the pod and PVC) and redeploy.

## Backup and restore

List dumps:

```bash
kubectl -n issue-tracker run backup-ls --rm -i --restart=Never --image=postgres:16 \
  --overrides='{"spec":{"containers":[{"name":"backup-ls","image":"postgres:16","command":["ls","-lt","/backups/daily","/backups/pre-migration"],"volumeMounts":[{"name":"b","mountPath":"/backups"}]}],"volumes":[{"name":"b","persistentVolumeClaim":{"claimName":"issue-tracker-backups"}}]}}'
```

Take one now: `kubectl -n issue-tracker create job backup-manual-$(date +%s) --from=cronjob/issue-tracker-backup-daily`.

Copy a dump off the cluster (keep it outside git): run a pod with the PVC mounted as above but
with `"command":["sleep","600"]`, then `kubectl -n issue-tracker cp backup-ls:/backups/daily/<file> ./<file>`.

Restore is manual and overwrites live data, so scale the app to zero first and pick the dump
deliberately:

```bash
NS=issue-tracker DUMP=/backups/pre-migration/<sha>-<ts>.dump
kubectl -n "$NS" scale deployment/issue-tracker --replicas=0
kubectl -n "$NS" apply -f - <<YAML
apiVersion: batch/v1
kind: Job
metadata:
  name: restore-$(date +%s)
spec:
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: restore
          image: postgres:16
          envFrom: [{secretRef: {name: issue-tracker-db}}]
          env:
            - {name: PGHOST, value: issue-tracker-postgres}
            - name: PGPASSWORD
              valueFrom: {secretKeyRef: {name: issue-tracker-db, key: POSTGRES_PASSWORD}}
          command: ["sh", "-euc", "pg_restore -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" --clean --if-exists --no-owner $DUMP"]
          volumeMounts: [{name: b, mountPath: /backups, readOnly: true}]
      volumes: [{name: b, persistentVolumeClaim: {claimName: issue-tracker-backups}}]
YAML
kubectl -n "$NS" get jobs -w     # wait for the restore Job to complete, then read its logs
kubectl -n "$NS" scale deployment/issue-tracker --replicas=1
kubectl -n "$NS" rollout status deployment/issue-tracker
```

To restore a dump from outside the cluster (e.g. the Compose production dump in step 11), first
copy it onto the backup PVC with a `sleep` pod and `kubectl cp`, then use its path as `DUMP`.

## Rollback

Never `alembic downgrade`, and never delete a PVC or namespace to "reset".

1. **App only (no schema change between the two SHAs):** re-run the pipeline on the previous good
   commit (Actions → Run workflow → pick the commit/branch), or directly:
   `kubectl -n <ns> set image deployment/issue-tracker app=ghcr.io/spacemanspiff99/issue-tracker:<previous-sha>`.
2. **Schema changed:** the old image may not run on the new schema. Scale the app to zero, restore
   the `pre-migration/<bad-sha>-<ts>.dump` taken before the bad migration (procedure above), then
   roll the Deployment back to the previous image as in 1. Data written after that dump is lost;
   export it first if it matters.

## Verified in CI

The CI `k8s` job renders both overlays, runs `kubeconform -strict`, scans `deployment/k8s` for
secret values, then on a kind cluster runs `deployment/k8s/tests/kind-smoke.sh`: two full deploys
of the `uat` overlay, a migrate Job that must refuse without a backup, CronJob retention (14 + 5),
and `e2e.sh`.
