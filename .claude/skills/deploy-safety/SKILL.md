---
name: deploy-safety
description: Use when editing `deployment/` (Dockerfile, compose files, `remote-compose-deploy.sh`), `.github/workflows/`, `.env.example` or config env vars, backup/restore docs, `deployment/k8s/`, or before dispatching or discussing a deploy to dev, UAT, or production (k3s `issue-tracker`). Covers IT-6 (deployment and configuration drift), the approval gate, and backup-before-migrate.
---

# Deploy Safety (IT-6)

## Facts (from `documentation/guides/k3s.md`, `documentation/guides/deployment.md`, the workflows)

- CI (`ci.yml`): ruff + pytest, Postgres `schema` job, Docker image build, compose `e2e` job.
  Runs on PRs and `main`.
- **PRODUCTION = k3s namespace `issue-tracker`**; UAT = `issue-tracker-uat` (owner decision
  2026-10-20). Procedure and owner steps: `documentation/guides/k3s.md`.
- `k3s-pipeline.yml` (dispatch only, self-hosted runner): `image.yml` pushes `:<sha>` and outputs
  the digest; UAT then prod deploy that digest via `deployment/k8s/deploy.sh <env> <image@sha256>
  <sha>` (backup Job → migrate Job checking that exact dump → rollout → `/health`).
  `deploy-prod` needs `promote_prod`, UAT success in the same run, and `environment: prod`
  (reviewer, `main` only); each environment has its own `K3S_KUBECONFIG` secret.
- `deployment/k8s/restore.sh` needs `CONFIRM=<namespace>`; `--require-empty` is for the first
  cutover only. Restores and rollbacks follow `k3s.md` (never `alembic downgrade`).
- **Retired:** Compose production on `192.168.10.8` (job removed in Issue 0038). Its data moves
  to k3s once, via `k3s.md` step 12. `local-pipeline.yml` is dev verify + legacy Compose UAT only.
- Compose hosts: dev `192.168.10.20`; legacy UAT `192.168.10.18` (replaced by k3s UAT for
  releases). User `akun`, path `/home/akun/issue-tracker`. Don't invent other hosts.
- Cloud sessions run in Anthropic's cloud and cannot reach `192.168.10.x` or the cluster; LAN
  and cluster steps run on the self-hosted runner or by the owner.
- `remote-compose-deploy.sh` refuses unsafe `DEPLOY_PATH`, refuses `SKIP_DB_BACKUP=1` when
  `DEPLOY_ENV` is `uat` or `prod` (exit 2), takes a `pg_dump` to
  `backups/<sha>-<ts>/pre-migration.dump`, runs `alembic upgrade head`, then requires `/health`
  to report `"database": "ok"`.
- `mirror-rules.yml` (on `main`): copies `CLAUDE.md` + `.claude/` and Codex/Cursor files into
  `vibecoding/projects/issue-tracker/`.

## Gates

- Dispatching any pipeline, SSHing to a host, running `kubectl` against the cluster, or
  migrating a non-local DB needs explicit user approval for that run. Production (k3s
  `issue-tracker`) additionally needs UAT (`issue-tracker-uat`) green on the same SHA first.
- Never set `SKIP_DB_BACKUP=1` for UAT or production. No backup → no migration.
- Releases run only `alembic upgrade head`. No downgrade, drop, reset, volume removal, or
  auto-restore.

## Config change checklist

A new/renamed env var updates all of: `config.py`, `.env.example`, both compose files,
`documentation/guides/deployment.md`, and the workflow env blocks if they set it.

## Verify

`docker compose -f deployment/docker-compose.local.yml config` (and `docker-compose.app.yml`),
`docker build -f deployment/Dockerfile .`, and after any deploy `curl -fsS $APP_BASE_URL/health`
showing `"database": "ok"`.
