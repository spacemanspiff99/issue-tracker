# Issue 0020: Deploy UAT And Production To The Home-Lab k3s Cluster

Status: backlog
Recommended model: claude-opus-5-5 high
Category gates: `IT-6`, `IT-3`, `IT-5`
Sprint: Sprint 0007

## Problem

The owner wants production on the home-lab k3s cluster instead of Docker Compose on `192.168.10.8`, with UAT tested on the same platform first. Today's pipeline (`local-pipeline.yml`) only SSHes Compose deploys to hosts.

## Decisions (owner, 2026-10-20)

- Deploy path: existing self-hosted runner (`self-hosted, issue-tracker, local-dev`) runs `kubectl` with a kubeconfig the owner provisions on the runner. No cloud session reaches the cluster.
- Database: in-cluster Postgres StatefulSet + PVC per namespace; backups by `pg_dump`.
- Image: built by GitHub Actions, pushed to `ghcr.io/spacemanspiff99/issue-tracker:<sha>`; cluster pulls with an imagePullSecret.
- Namespaces: `issue-tracker-uat` (UAT) and `issue-tracker` (production). UAT on k3s replaces the `.18` Compose UAT for releases.

## Scope

- `deployment/k8s/`: kustomize base (app Deployment, Service, Ingress, Postgres StatefulSet + headless Service + PVC, ConfigMap, Secret *template only*, pre-deploy backup Job, migration Job, backup CronJob) and overlays `uat` and `prod`. Storage class, ingress host, and resources are overlay values with documented defaults.
- App container never migrates on start: migration is a Job (`alembic upgrade head`) run by the pipeline after a backup Job succeeds.
- Liveness/readiness on `/health`; readiness requires `"database": "ok"`.
- `.github/workflows/image.yml`: build + push image to GHCR on `main` and on dispatch, tagged with the SHA.
- `.github/workflows/k3s-pipeline.yml` (dispatch only): deploy SHA to `issue-tracker-uat` → backup Job → migrate Job → rollout → `/health` → Playwright e2e against UAT URL; then optional `promote_prod` (default false, `environment: prod` with required reviewer) on the same SHA with backup → migrate → rollout → `/health`.
- `documentation/guides/k3s.md`: owner setup (kubeconfig on runner, namespaces, GHCR pull secret, app/DB secrets, storage class, DNS/ingress), deploy, backup/restore from the backup PVC, rollback (redeploy previous image; restore DB from pre-migration dump; never `alembic downgrade`).
- No real secrets in git; Secret manifests are examples with placeholder values and are excluded from `kustomize build` defaults.

## Acceptance Criteria

- [ ] `kubectl kustomize deployment/k8s/overlays/uat` and `.../prod` render cleanly; `kubeconform -strict` (or equivalent) passes on both, run in CI.
- [ ] A local kind or k3d cluster in CI/cloud: deploy the `uat` overlay with a locally built image, backup Job then migrate Job complete, app rollout ready, `/health` returns `"database": "ok"`, and `tests/e2e` passes against it (if 0014's suite is merged).
- [ ] Prod job cannot run without UAT success on the same SHA in the same run, and never skips the backup Job.
- [ ] No secret values in git (`git grep` for password/token patterns clean; secret manifests are `*.example.yaml`).
- [ ] `documentation/guides/k3s.md` lists every owner action, in order, with exact commands.
- [ ] `documentation/guides/deployment.md` points to k3s for UAT/prod; Compose stays documented for local dev only.

## Category Checklists

`IT-6` Deployment And Configuration Drift: env vars, health checks, explicit migrations, and workflow behavior stay aligned across overlays.
`IT-3` Schema: migration runs as a Job after a backup; never downgrade in a release.
`IT-5` Auth And Secret Safety: secrets only via k8s Secrets created by the owner; session cookie settings unchanged.

## STOP

Stop when every AC passes in a disposable cluster, or record which AC need the owner's real cluster. Do not reach 192.168.10.x or the real cluster.
