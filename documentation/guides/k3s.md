# k3s Deployment Guide (UAT And Production)

UAT and production run on the home-lab k3s cluster (issue 0020; hardened before the first run in issues 0039 and 0041). Docker Compose stays for local
development only (`local-development.md`).

| Environment | Namespace | Overlay | Default ingress host |
| --- | --- | --- | --- |
| UAT | `issue-tracker-uat` | `deployment/k8s/overlays/uat` | `issue-tracker-uat.home.arpa` |
| **Production** | `issue-tracker` | `deployment/k8s/overlays/prod` | `issue-tracker.home.arpa` |

Images: `ghcr.io/spacemanspiff99/issue-tracker:<git-sha>`, built by `.github/workflows/image.yml`.
The pipeline deploys the pushed **digest** (`...@sha256:...`), so UAT and production run the same
bytes.
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
  restore.sh            all-or-nothing restore of a dump from the backup PVC (CONFIRM=<ns>)
  restore-job.sh        what the restore Job runs (safety dump, guard, one-transaction restore)
  backup-files.sh       list / copy off / upload dumps on the backup PVC
  e2e.sh                Playwright workflow suite in a one-off pod against the UAT Service;
                        screenshots to artifacts/e2e-k8s (uploaded by the pipeline); refuses prod
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
| `issue-tracker-backups` | 1Gi | 14 daily dumps + the 5 newest pre-migration and 5 newest pre-restore dumps; older ones pruned |

UAT + production request 6Gi. Multiply by the storage class replica count for raw usage (Longhorn
3 replicas = 18Gi). UAT may use a 1-replica class.

## Owner actions, in order

Run these from a machine with cluster-admin access (not from a cloud session). Steps 1–9 and 12 are
one-time. Step 10 is every release, and step 11 adds production to it.

All scripts check that the kubectl context is named `issue-tracker-uat` or `issue-tracker-prod`
(steps 3 and 9 create those contexts). Locally, point `KUBECONFIG` at the matching file before
running `restore.sh` or `backup-files.sh`.

**1. Runner tools.** On the self-hosted runner (as the runner user `github`), install `kubectl`
(within one minor version of the cluster), `bash`, `curl` and `python3`:

```bash
kubectl version --client && python3 --version && curl --version | head -1
```

**2. Namespaces.**

```bash
kubectl create namespace issue-tracker-uat
kubectl create namespace issue-tracker
```

**3. One deploy identity per environment.** Each ServiceAccount is `admin` in its own namespace and
has no cluster-scope rights. Each kubeconfig goes only to its matching GitHub environment, so the
production token is released only after the `prod` reviewer approves.

```bash
make_kubeconfig() {  # make_kubeconfig <env-name> <namespace> <output file>
  local env="$1" ns="$2" out="$3" server token
  kubectl -n "$ns" create serviceaccount issue-tracker-deployer
  kubectl -n "$ns" create rolebinding issue-tracker-deployer \
    --clusterrole=admin --serviceaccount="$ns:issue-tracker-deployer"
  token="$(kubectl -n "$ns" create token issue-tracker-deployer --duration=8760h)"
  server="$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')"
  kubectl config view --minify --raw -o jsonpath='{.clusters[0].cluster.certificate-authority-data}' \
    | base64 -d > /tmp/k3s-ca.crt
  kubectl --kubeconfig "$out" config set-cluster k3s --server="$server" \
    --certificate-authority=/tmp/k3s-ca.crt --embed-certs=true
  kubectl --kubeconfig "$out" config set-credentials "issue-tracker-$env" --token="$token"
  kubectl --kubeconfig "$out" config set-context "issue-tracker-$env" --cluster=k3s \
    --user="issue-tracker-$env" --namespace="$ns"
  kubectl --kubeconfig "$out" config use-context "issue-tracker-$env"
  rm -f /tmp/k3s-ca.crt
}
umask 077
mkdir -p ~/.kube
make_kubeconfig uat issue-tracker-uat ~/.kube/issue-tracker-uat.yaml
make_kubeconfig prod issue-tracker ~/.kube/issue-tracker-prod.yaml
chmod 600 ~/.kube/issue-tracker-uat.yaml ~/.kube/issue-tracker-prod.yaml
# Each file can act only in its own namespace:
KUBECONFIG=~/.kube/issue-tracker-uat.yaml  kubectl -n issue-tracker-uat auth can-i create jobs   # yes
KUBECONFIG=~/.kube/issue-tracker-uat.yaml  kubectl -n issue-tracker     auth can-i get secrets   # no
KUBECONFIG=~/.kube/issue-tracker-prod.yaml kubectl -n issue-tracker     auth can-i create jobs   # yes
KUBECONFIG=~/.kube/issue-tracker-prod.yaml kubectl -n issue-tracker-uat auth can-i get secrets   # no
```

Store each file as an **environment secret** named `K3S_KUBECONFIG`: under **Settings → Environments
→ uat → Environment secrets** paste `~/.kube/issue-tracker-uat.yaml`, and under **prod** paste
`~/.kube/issue-tracker-prod.yaml`. Never use a repository variable or secret for these.

Keep both files on your admin machine only, mode `0600`, in `~/.kube/`. Steps 11 and 12,
"Off-cluster copies" and "Restore" use them with `restore.sh` and `backup-files.sh`. Never copy
them to the runner, the repo, or a cloud session. If one is lost or exposed, revoke it
(`kubectl -n <ns> delete serviceaccount,rolebinding issue-tracker-deployer`), rerun
`make_kubeconfig` for that environment, and update its environment secret. The pipeline writes the secret to a `0600` temp file, sets `KUBECONFIG`, and deletes the
file at the end of the job. It fails if the secret is empty, and `deploy.sh` refuses a context that
isn't named `issue-tracker-<env>`. Tokens expire after a year: rerun the `create token` and
`set-credentials` lines and update both the file and the environment secret.

**4. GHCR pull secret** (per namespace). Create a GitHub PAT (classic) with only `read:packages`:

```bash
for ns in issue-tracker-uat issue-tracker; do
  kubectl -n "$ns" create secret docker-registry ghcr-pull --docker-server=ghcr.io \
    --docker-username=spacemanspiff99 --docker-password='<PAT with read:packages>'
done
```

**5. App and database Secrets** (per namespace, with different values in each). The DB password is
embedded in `DATABASE_URL`, so keep it hex:

```bash
kubectl -n issue-tracker-uat create secret generic issue-tracker-db \
  --from-literal=POSTGRES_USER=issue_tracker --from-literal=POSTGRES_DB=issue_tracker \
  --from-literal=POSTGRES_PASSWORD="$(openssl rand -hex 24)"
kubectl -n issue-tracker-uat create secret generic issue-tracker-app \
  --from-literal=APP_SECRET_KEY="$(openssl rand -hex 32)" \
  --from-literal=ADMIN_INITIAL_PASSWORD='<UAT admin password; the browser suite logs in with it>'
# If the UAT admin password changes later, add the key the browser suite prefers:
#   kubectl -n issue-tracker-uat patch secret issue-tracker-app -p '{"stringData":{"E2E_ADMIN_PASSWORD":"<current>"}}'

kubectl -n issue-tracker create secret generic issue-tracker-db \
  --from-literal=POSTGRES_USER=issue_tracker --from-literal=POSTGRES_DB=issue_tracker \
  --from-literal=POSTGRES_PASSWORD="$(openssl rand -hex 24)"
kubectl -n issue-tracker create secret generic issue-tracker-app \
  --from-literal=APP_SECRET_KEY="$(openssl rand -hex 32)" \
  --from-literal=ADMIN_INITIAL_PASSWORD=
```

Never commit these values; `deployment/k8s/secrets/*.example.yaml` shows their shape only. The
Postgres password is fixed at the first `initdb`, so changing the Secret later does not change the
database role. To rotate it, run `ALTER ROLE` first, then update the Secret, then
`kubectl rollout restart`.

**6. Storage class.**

```bash
kubectl get storageclass
```

`local-path` needs no change. For Longhorn (or any other class), edit both `storageClassName`
values in each overlay before the first deploy; a StatefulSet volume claim template cannot be
changed afterwards. For a 1-replica UAT class:

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
hosts you set in the overlays) at the k3s node(s) running Traefik, either in the home-lab DNS or in
the runner's `/etc/hosts`.

**8. GitHub environments.** In **Settings → Environments**:
- `uat`: holds the UAT `K3S_KUBECONFIG` secret (step 3).
- `prod`: add a **required reviewer**, and set **Deployment branches and tags** to
  **Selected branches** with the single rule `main`. Production can then deploy only from `main`,
  and only after approval. Holds the production `K3S_KUBECONFIG` secret.

The pipeline enforces `main` itself as well:
- `Deploy PRODUCTION` fails unless `github.ref` is `refs/heads/main`.
- `Deploy UAT` fails on any other ref, unless you set `allow_non_main_uat: true` for a UAT-only
  test of a branch. `promote_prod: true` from a branch is refused even with that override.

**9. First UAT deploy.** After this PR is merged, go to Actions → **k3s UAT Production Pipeline** →
Run workflow on `main` with `promote_prod: false`. The run log should show:
- the pushed image digest
- the backup Job writing `/backups/pre-migration/<sha>-<ts>.dump`
- the migrate Job checking that exact file, then running `alembic upgrade head`
- rollout complete
- `health: {"ok": true, "database": "ok"}`, both in the pod and through the ingress
- the browser suite passing, with screenshots in the `uat-e2e-screenshots-<sha>` artifact

**10. Every release.** Production always takes an image that UAT has already verified:
1. Run the pipeline on `main` with `promote_prod: false`. Copy the digest from the run (the
   `image / push` log: `pushed ...@sha256:...` or `already pushed: ...`).
2. Check UAT.
3. Run the pipeline on `main` again with `promote_prod: true` and `expected_image: <that digest>`.

`promote_prod: true` without `expected_image` is refused. The second run reuses the image (an
already-pushed SHA is never rebuilt), redeploys it to UAT, then promotes it. If the digest
differs, both deploy jobs refuse; start again from step 1. That happens when `main` moved in
between, or when the tag in GHCR was deleted or overwritten since the first run. A push-to-main
image build and a pipeline run for the same commit don't race: both use the concurrency group
`image-<sha>`, so the second waits for the first and reuses its digest. A *third* run for the same
SHA while one is still waiting replaces it: GitHub cancels the waiting image job, and that run
ends as cancelled before any deploy step (nothing is deployed); start it again.

**11. First production deploy.** Run the pipeline with `promote_prod: true` and `expected_image`
(as in step 10). `Deploy PRODUCTION
(k3s)` runs only after `Deploy UAT (k3s)` succeeded in the same run (and so on the same commit). It
deploys only the digest that UAT ran (checked against the live UAT Deployment), waits for the
`prod` reviewer, and runs the same backup → migrate → rollout → `/health` sequence. The first run
creates Postgres and an empty schema at head. Then, with your cluster-admin kubeconfig (patching a
PV is cluster-scope, so the deploy identities can't do it), make sure deleting a PVC can never
delete the production data:

```bash
for pvc in data-issue-tracker-postgres-0 issue-tracker-backups; do
  pv="$(kubectl -n issue-tracker get pvc "$pvc" -o jsonpath='{.spec.volumeName}')"
  kubectl patch pv "$pv" -p '{"spec":{"persistentVolumeReclaimPolicy":"Retain"}}'
done
kubectl get pv | grep issue-tracker/   # RECLAIM POLICY must read Retain
```

**12. Move production data off Compose (once), rehearsed on UAT first.** The Compose production at
`192.168.10.8` holds the real data.

a. **Stop every writer on `.8`.** Stop the web app container, and close or reconfigure every MCP
   client (Claude Code/Codex/Cursor sessions) that points at the `.8` tracker. Then dump the
   database and record its migration head:

```bash
# On 192.168.10.8 in /home/akun/issue-tracker/current
docker compose -f deployment/docker-compose.local.yml stop app
docker compose -f deployment/docker-compose.local.yml exec -T postgres \
  psql -U issue_tracker -d issue_tracker -Atc 'select version_num from alembic_version'
docker compose -f deployment/docker-compose.local.yml exec -T postgres \
  pg_dump -U issue_tracker -d issue_tracker -Fc > /home/akun/issue-tracker/backups/to-k3s.dump
pg_restore -l /home/akun/issue-tracker/backups/to-k3s.dump > /dev/null && echo dump readable
```

   If the head is older than the newest file in `migrations/versions/`, the first k3s deploy after
   the restore will migrate it forward. `0004_reconcile_schema_drift` refuses to run (and the
   deploy stops before rollout) if any `guidance_*` table has rows or an FK column has NULLs. The
   UAT rehearsal below finds that before production does.

b. **Rehearse on UAT.** Copy the dump to the machine with the kubeconfigs, then:

```bash
export KUBECONFIG=~/.kube/issue-tracker-uat.yaml
deployment/k8s/backup-files.sh uat put ./to-k3s.dump to-k3s.dump
CONFIRM=issue-tracker-uat deployment/k8s/restore.sh uat /backups/imports/to-k3s.dump --keep-app-down
```

   `--keep-app-down` leaves the UAT app at 0: the restored data may be at an older migration head
   than the running image expects. Next, run the pipeline on `main` with `promote_prod: false`; that
   deploy migrates the data and brings the app up. It must back up, migrate the restored
   data to head, pass `/health` and pass the browser suite. Check the projects and issues in the UAT
   UI. If the migrate Job fails, stop: fix the data or the migration in a new issue before going
   further. Nothing in production has changed.

   **Record the rehearsal's image digest.** It is in the run's `image / push` job log
   (`pushed ghcr.io/...@sha256:...` or `already pushed: ...`) and in the `Deploy UAT` log as
   `image: ...@sha256:...`. The cutover must run that exact digest.

c. **Production.** With the rehearsal green, and Compose still stopped:

```bash
export KUBECONFIG=~/.kube/issue-tracker-prod.yaml
deployment/k8s/backup-files.sh prod put ./to-k3s.dump to-k3s.dump
CONFIRM=issue-tracker deployment/k8s/restore.sh prod /backups/imports/to-k3s.dump --require-empty --keep-app-down
```

   `--require-empty` makes the restore refuse unless the k3s production `projects` table is absent or
   empty. `--keep-app-down` leaves the app at 0 until the next deploy migrates the data and brings
   it up. Next, run the pipeline on `main` with `promote_prod: true` and
   `expected_image: <the rehearsal digest>`. Both deploy jobs refuse if this run would deploy any
   other digest. That happens if `main` moved since the rehearsal, or if the GHCR tag was deleted or
   overwritten (an already-pushed SHA is otherwise never rebuilt). If it refuses, rehearse again
   on the new commit (step 12b) rather than skipping the check. Production backs up the restored data and migrates it forward.
   Check projects and issues in the UI, then switch DNS and bookmarks. Leave the Compose stack
   stopped, not removed, until you are satisfied. (`local-pipeline.yml` has no production job
   since issue 0038, so nothing can deploy to `.8` again.)

## What a deploy does (`deploy.sh <uat|prod> <image@sha256:...> <sha>`)

1. Validates its inputs and renders the manifests with the image pinned. Then it refuses unless the
   kubectl context is `issue-tracker-<env>`.
2. Preflight: the Secrets `issue-tracker-db` and `issue-tracker-app` exist (it never creates them).
   It warns if `ghcr-pull` is missing. It refuses if a backup, migrate or restore Job is still
   active, or a restore pod is still running without one (checked again just before the backup),
   then takes the restore lock (see Restore) for the rest of the run, so no restore can
   start during the deploy.
3. Applies everything except the app (ConfigMap, Postgres, PVCs, CronJob) and waits for Postgres.
   **Maintenance window:** it scales the app to 0 and waits for its pod to go; if the pod is still
   there at the timeout, the deploy aborts before the backup. If a step fails or times out before
   the rollout, it first deletes the backup and migrate Jobs and waits until their pods are gone.
   With its client gone, an unfinished migration can never send `COMMIT`. Then it re-reads
   `alembic_version`:
   - unchanged from before the deploy: the previous app is scaled back up
   - changed, unreadable (for example locked by another session), or Jobs not confirmed gone:
     **the app stays at 0** and the log says what to check (see "Found the app at 0 replicas")

   The cleanup ignores further Ctrl-C/TERM signals, so a second one doesn't cut it short; each of
   its steps is bounded (the Job deletion waits at most 180s).
   **A cancelled run is different.** GitHub signals the step's shell and force-kills it about
   10 seconds later, which is usually before the cleanup above can finish. Expect the app at 0,
   with the migrate Job possibly still running, and follow "Found the app at 0 replicas". Don't
   cancel a deploy that is past the backup unless it is stuck. A killed run may also leave the
   restore lock behind; the next deploy or restore then refuses and says how to clear it (see
   Restore).
4. Picks the backup path `/backups/pre-migration/<sha>-<ts>.dump` and runs
   `issue-tracker-backup-predeploy` to write exactly that file. The dump is verified with
   `pg_restore -l`, leftover `.partial` files are removed, and the newest 5 dumps are kept.
5. Runs `issue-tracker-migrate`. Its init container checks that same file and refuses if it is
   missing or unreadable; the Job then runs `alembic upgrade head`. No flag skips the backup, and
   nothing runs `alembic downgrade`.
6. Applies the app Deployment, Service and Ingress (replicas back to 1) and waits for rollout. The container never
   migrates on start. Readiness requires `/health` to return `"database": "ok"`; liveness is
   `/health`.
7. Checks `/health` from inside the pod. The pipeline also checks the ingress URL.

**One-time Postgres restart (issue 0041).** The Postgres probes now check over TCP. On a namespace
deployed before that change, the first deploy afterwards changes the StatefulSet's pod template, so
Kubernetes restarts the Postgres pod once during step 3, while the old app is still up. Expect a few
seconds of `/health` failing on the old app; the deploy waits for the new pod before it continues.
Later deploys don't restart Postgres.

`RENDER_ONLY_DIR=<dir> deploy.sh ...` writes the exact manifests to `<dir>` and touches no cluster.
CI uses it.

**Why the maintenance window.** With the app running, a write after the `pg_dump` would be
missing from the pre-migration dump, so restoring that dump after a bad migration would lose
it. The old code would also run against the new schema between the migration and the rollout.
Scaling the app to 0 for backup + migrate closes both gaps. The cost is a short outage
(typically about a minute: pod stop, dump, migrate, new pod ready), and UAT goes through the same
window so production behaves as rehearsed. The rollback is safe because Alembic runs every
revision in one transaction on Postgres (`migrations/env.py`): a failed migration leaves the
schema as it was. stdio MCP clients write to the database directly and are not stopped by the
window; avoid MCP writes while a deploy runs.

The daily CronJob (`03:17` UTC) writes `/backups/daily/<ts>.dump` and keeps 14 daily dumps and
the 5 newest pre-migration and pre-restore dumps.

## Off-cluster copies

The backup PVC lives on the same cluster as the database. At least weekly, and before any risky
change, copy the newest dumps somewhere else, such as the NAS:

```bash
export KUBECONFIG=~/.kube/issue-tracker-prod.yaml
deployment/k8s/backup-files.sh prod get-latest /mnt/nas/issue-tracker-backups/$(date +%F)
```

`backup-files.sh prod list` shows every dump and `df -h /backups`.

## Storage checks

```bash
kubectl get pvc -A | grep issue-tracker
kubectl -n issue-tracker exec issue-tracker-postgres-0 -- df -h /var/lib/postgresql/data
kubectl -n issue-tracker exec issue-tracker-postgres-0 -- \
  sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "select pg_size_pretty(pg_database_size(current_database()))"'
deployment/k8s/backup-files.sh prod list
```

Longhorn: the Longhorn UI → Volumes shows actual vs. requested size. `local-path`: run
`df -h /var/lib/rancher/k3s/storage` on the node.

## Resizing a PVC

Resizing works only with storage classes that have `allowVolumeExpansion: true`. Longhorn does;
`local-path` does not (it doesn't enforce the size either, so a volume grows until the node disk
fills).

```bash
kubectl get storageclass <class> -o jsonpath='{.allowVolumeExpansion}'
kubectl -n issue-tracker patch pvc data-issue-tracker-postgres-0 \
  -p '{"spec":{"resources":{"requests":{"storage":"4Gi"}}}}'
kubectl -n issue-tracker patch pvc issue-tracker-backups \
  -p '{"spec":{"resources":{"requests":{"storage":"2Gi"}}}}'
kubectl -n issue-tracker get pvc -w
```

Then update the request in `base/` so a fresh install matches. The StatefulSet's volume claim
template is immutable: changing it in git does not resize the existing PVC, and applying it fails
until you run `kubectl -n <ns> delete statefulset issue-tracker-postgres --cascade=orphan` (this
keeps the pod and the PVC) and redeploy.

## Restore

`restore.sh` overwrites live data and runs only with `CONFIRM=<namespace>`. First close every MCP
session that points at this database: the stdio MCP server opens its own DB connection and doesn't
go through the web app. A restore can't start while a deploy runs (they share the restore lock
below), but wait for a pipeline run to finish anyway, so you restore what you meant to. The script
then:
- refuses if a backup, migrate or another restore Job is active, or a restore pod is still running
  without one
- takes the **restore lock**, the ConfigMap `issue-tracker-restore-lock`. The create is atomic, so a
  second `restore.sh`, or a `deploy.sh`, is refused while it is held, and `deploy.sh` takes the same
  lock for its whole run. Each holder writes its name in `data.job` and releases the lock on exit
  only if `data.job` still names it. It keeps the lock if its Jobs may still be running (an
  interrupted run, a timed-out restore Job it could not delete, or backup/migrate Jobs a failed
  deploy could not confirm gone) and says so. If a killed `restore.sh` or `deploy.sh` left the lock
  behind, check that nothing is running (`kubectl -n <ns> get jobs,pods`) and who held it
  (`kubectl -n <ns> get configmap issue-tracker-restore-lock -o jsonpath='{.data.job}'`), then
  `kubectl -n <ns> delete configmap issue-tracker-restore-lock`.
- scales the app to zero, and checks again for an active restore Job or a live restore pod just
  before it creates its own
- runs a Job (`restore-job.sh`) that:
  - logs `alembic_version` before the restore, and again after it (or after a failure)
  - removes every pin in `/backups/restoring/` but its own (leaked by restore Jobs that were
    killed; no other restore pod can be live), then pins the dump with a hard link there, so no
    prune can delete it mid-restore, and checks it with `pg_restore -l`
  - writes a **safety dump of the current database** to `/backups/pre-restore/<ts>-<pod>.dump`
    (after a successful restore the newest 5 are kept, never counting or deleting the dump that
    was just restored)
  - in one `psql` transaction with `ON_ERROR_STOP`: (with `--require-empty`) refuses if
    `projects` has rows, then runs `DROP SCHEMA public CASCADE; CREATE SCHEMA public;` and the
    whole restore. The guard passes when `projects` is absent or empty.

Because everything is one transaction, any error rolls back to the database as it was, and objects
from a bad migration don't survive. This gives the same all-or-nothing behavior as
`pg_restore --single-transaction --exit-on-error`, and extends it to cover the schema drop.

Outcomes:
- **Succeeded, same `alembic_version` before and after:** the app goes back to its previous replica
  count (an app that was at 0 stays at 0), or stays at 0 with `--keep-app-down`.
- **Succeeded, but `alembic_version` changed** (for example a `pre-migration` dump restored after a
  deploy migrated past it), or the Job logs can't be read: the app **stays at 0**, because its
  current image may not match the restored schema. The script exits non-zero and prints both
  versions; follow Rollback 2 (`set image` to an image that matches, then scale up), or run the
  pipeline, whose deploy migrates the restored data forward and brings the app up.
- **Failed before `COMMIT`**, and the Job re-read the same `alembic_version` on its way out
  (the script prints "revision unchanged"): the app goes back to its previous replica count, or stays at 0 if it
  was at 0 or `--keep-app-down` was given. A changed or missing version leaves the app at 0.
- **Failed, and the logs can't show whether it committed** (unreadable, or a version line missing or
  repeated): the app stays at 0; check as in "Found the app at 0 replicas".
- **Timed out** (`RESTORE_TIMEOUT_SECONDS`, default 600): the script deletes the Job so an
  uncommitted transaction rolls back. It **leaves the app at 0 replicas**, because the
  transaction may have committed just before the deletion. Check `select version_num from
  alembic_version` and the project count, then scale up with the command the script prints.

If a restore itself was the mistake, restore the safety dump it took:
`CONFIRM=<ns> restore.sh <env> /backups/pre-restore/<ts>-<pod>.dump`.

```bash
deployment/k8s/backup-files.sh prod list
# A pre-migration dump is at the revision BEFORE that deploy's migration: keep the app down and
# set the matching image as in Rollback 2 before scaling up.
CONFIRM=issue-tracker deployment/k8s/restore.sh prod /backups/pre-migration/<sha>-<ts>.dump --keep-app-down
```

To restore a dump from outside the cluster, upload it first with
`backup-files.sh <env> put <file> <name>.dump`, then use `/backups/imports/<name>.dump`.

## Found the app at 0 replicas

A failed or cancelled deploy, a timed-out restore, a restore that aborted because the app pod
wouldn't stop (or its pods couldn't be listed), a restore that changed `alembic_version`, or
`restore.sh --keep-app-down` can leave the app at 0. The
script's last log lines say why. Before scaling up, check that the image and the schema match:

```bash
NS=issue-tracker   # or issue-tracker-uat
kubectl -n $NS get deployment issue-tracker -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
kubectl -n $NS get jobs,pods                     # no issue-tracker-migrate / -restore-* pod still running
kubectl -n $NS exec issue-tracker-postgres-0 -- sh -c \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "select version_num from alembic_version" -c "select count(*) from projects"'
```

- **No Job running, version as before the deploy:** scale up:
  `kubectl -n $NS scale deployment/issue-tracker --replicas=1`.
- **Version is newer (the migration committed):** re-run the pipeline on the same commit to
  finish the deploy, or roll back (below).
- **A migrate or restore pod is still running or stuck:** look at its logs and at
  `pg_stat_activity` for the session it waits on (often an MCP client). Close that session or
  terminate it, let the Job finish or delete it, then check again.

## Rollback

Never run `alembic downgrade`, and never delete a PVC or namespace to "reset".

1. **App only (no schema change between the two commits):** the pipeline deploys only the tip of
   `main`, so either `git revert` the bad commit on `main` and run the pipeline, or point the
   Deployment at the previous digest directly:
   `kubectl -n <ns> set image deployment/issue-tracker app=ghcr.io/spacemanspiff99/issue-tracker@<previous digest>`.
2. **Schema changed:** the new image must not start on the old schema, and the old image must not
   start on the new one. Do it in this order (data written after the dump is lost, so copy it off
   first with `backup-files.sh get-latest` if it matters):

   ```bash
   CONFIRM=issue-tracker deployment/k8s/restore.sh prod /backups/pre-migration/<bad-sha>-<ts>.dump --keep-app-down
   kubectl -n issue-tracker set image deployment/issue-tracker app=ghcr.io/spacemanspiff99/issue-tracker@<previous digest>
   kubectl -n issue-tracker scale deployment/issue-tracker --replicas=1
   kubectl -n issue-tracker rollout status deployment/issue-tracker
   ```

   **UAT has the bad revision too** (it ran first). Before a `git revert` on `main` can pass the
   pipeline's UAT stage, restore UAT the same way from its own
   `pre-migration/<bad-sha>-<ts>.dump`, using `restore.sh uat` with the UAT kubeconfig. Otherwise
   the reverted code meets a database at a revision it doesn't know, and `alembic upgrade head`
   fails.

## Verified in CI

The CI `k8s` job does the following:
- renders both overlays and runs `kubeconform -strict`
- renders both deploys pinned by digest and checks that the backup and migrate Jobs share one path
- checks that `deploy.sh` rejects bad inputs, and that every Postgres image is pinned to `16.15`
- runs the pipeline's ref and digest gate steps under every combination of inputs
  (`deployment/k8s/tests/pipeline-gates.py`)
- scans `deployment/k8s` for secret values
- on a kind cluster, runs `deployment/k8s/tests/kind-smoke.sh`, which covers:
  - refusing the wrong context
  - two deploys of the `uat` overlay: the no-op redeploy leaves the Postgres pod and revision
    unchanged, and the app pod is replaced (maintenance window)
  - a migrate Job refusing without its backup
  - refusing to deploy while a migrate or restore Job is active
  - CronJob retention (14 + 5)
  - `restore.sh --require-empty` passing with an empty and with an absent `projects` table, and a
    safety dump written before each restore
  - the browser suite
  - copying backups off the cluster and uploading them back
  - `restore.sh` refusing without `CONFIRM`, with `--require-empty` on a non-empty database, and
    while another restore is active
  - a timed-out restore: Job deleted, app left at 0, data unchanged
  - a migration blocked on a lock past its timeout: migrate Job deleted, app left at 0 because
    `alembic_version` can't be read, version unchanged afterwards
  - a failing backup: no migration, Jobs deleted, version unchanged, old app back
  - `restore.sh --keep-app-down` leaving the app at 0
  - a full restore that removes a leftover table and returns `/health` ok
