---
name: deploy-safety
description: Use when editing `deployment/` (Dockerfile, compose files, `remote-compose-deploy.sh`), `.github/workflows/`, `.env.example` or config env vars, backup/restore docs, `deployment/k8s/`, or before dispatching or discussing a deploy to dev, UAT, or production (k3s `issue-tracker`). Covers IT-6 (deployment and configuration drift), the approval gate, and backup-before-migrate.
---

# Deploy Safety (IT-6)

## Facts (from `documentation/guides/deployment.md`, `.github/workflows/local-pipeline.yml`, Issue 0020)

- CI (`ci.yml`): ruff + pytest, Postgres `schema` job, Docker image build, compose `e2e` job.
  Runs on PRs and `main`.
- **PRODUCTION = k3s namespace `issue-tracker`**; UAT = `issue-tracker-uat` (owner decision
  2026-10-20). The self-hosted runner deploys with `kubectl`; image from GHCR. `deployment/k8s/`
  and `k3s-pipeline.yml` are Issue 0020 and don't exist yet: until then there is **no supported
  production deploy**.
- **Retired:** Compose production on `192.168.10.8`. `local-pipeline.yml` still has its job
  (`deploy-prod`, inputs `prod_host`/`promote_prod`, `environment: prod`, `needs: deploy-uat`,
  refuses a SHA other than UAT's). Never dispatch with `promote_prod: true`; removal is Issue 0038.
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
