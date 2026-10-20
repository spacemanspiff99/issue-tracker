---
name: deploy-safety
description: Use when editing `deployment/` (Dockerfile, compose files, `remote-compose-deploy.sh`), `.github/workflows/`, `.env.example` or config env vars, backup/restore docs, or before dispatching or discussing a deploy to a dev/UAT host. Covers IT-6 (deployment and configuration drift), the approval gate, and backup-before-migrate.
---

# Deploy Safety (IT-6)

## Facts (from `documentation/guides/deployment.md`, `.github/workflows/local-pipeline.yml`)

- CI (`ci.yml`): ruff + pytest on host Python 3.12, and a Docker image build. Runs on PRs and `main`.
- `local-pipeline.yml` (manual dispatch, self-hosted runner): verify current dev
  (`192.168.10.20`) → deploy UAT (`192.168.10.18`, backup + browser UAT) → optional downstream dev
  (`192.168.10.8`). User `akun`, path `/home/akun/issue-tracker`. Hosts come from the workflow
  inputs/defaults — don't invent others.
- `remote-compose-deploy.sh` refuses unsafe `DEPLOY_PATH`, takes a `pg_dump` to
  `backups/<sha>-<ts>/pre-migration.dump` unless `SKIP_DB_BACKUP=1`, runs `alembic upgrade head`,
  then checks `/health`.
- `mirror-rules.yml` (on `main`): copies `CLAUDE.md` + `.claude/` and Codex/Cursor files into
  `vibecoding/projects/issue-tracker/`.

## Gates

- Dispatching `local-pipeline.yml`, SSHing to a host, or running a migration on a non-local DB
  needs explicit user approval for that run.
- Never set `SKIP_DB_BACKUP=1` for UAT/downstream dev. No backup → no migration.
- Releases run only `alembic upgrade head`. No downgrade, drop, reset, volume removal, or
  auto-restore.

## Config change checklist

A new/renamed env var updates all of: `config.py`, `.env.example`, both compose files,
`documentation/guides/deployment.md`, and the workflow env blocks if they set it.

## Verify

`docker compose -f deployment/docker-compose.local.yml config` (and `docker-compose.app.yml`),
`docker build -f deployment/Dockerfile .`, and after any deploy `curl -fsS $APP_BASE_URL/health`
showing `"database": "ok"`.
