# Deployment Guide

Use `deployment/docker-compose.app.yml` when PostgreSQL is external. Provide environment variables through your deployment system or an uncommitted `.env` file.

Required variables:

- `DATABASE_URL`
- `APP_SECRET_KEY`
- `APP_BASE_URL`
- `ADMIN_USERNAME`
- `SESSION_COOKIE_SECURE`
- `MCP_ENABLED`
- `LOG_LEVEL`

Optional first-run variable:

- `ADMIN_INITIAL_PASSWORD`

Apply migrations explicitly before starting or updating the app:

```bash
docker compose -f deployment/docker-compose.app.yml run --rm app alembic upgrade head
docker compose -f deployment/docker-compose.app.yml up -d
```

Verify health after migrations and startup:

```bash
curl -fsS "$APP_BASE_URL/health"
```

The app never auto-drops, recreates, truncates, or silently migrates production databases.

## Release Data Safety Rules

Release updates may run forward-only Alembic migrations, but they must not delete existing tracker data as part of normal deploy. Treat data changes as release-critical:

- Take a PostgreSQL backup before running migrations on UAT or production-like hosts.
- Run only `alembic upgrade head` during deploy. Do not run downgrade, drop, truncate, reset, or recreate commands in a release pipeline.
- If the backup cannot be created or copied to the host backup folder, stop the deployment before migration.
- Verify `/health` after migration and startup.
- Keep backups outside git under the host deployment backup folder.
- Use a reviewed migration for schema/data transforms; do not hide destructive cleanup in app startup.

The local runner pipeline creates a compressed custom-format `pg_dump` before migrations:

```text
/home/akun/issue-tracker/backups/<sha>-<timestamp>/pre-migration.dump
```

Restore is intentionally manual. Inspect the target and use PostgreSQL tools such as `pg_restore` from a known-good backup; do not add automatic restore or rollback that could overwrite live data without human approval.

## Local Runner Dev -> UAT -> Dev Pipeline

Use `.github/workflows/local-pipeline.yml` for the local network pipeline:

1. Verify the current self-hosted runner checkout with Docker build, Alembic, tests, MCP smoke, and ruff.
2. Deploy the verified source tree to UAT at `akun@192.168.10.18`.
3. Run UAT health, MCP smoke, and browser UAT on the UAT host.
4. Optionally promote the same revision to downstream dev at `akun@192.168.10.8`.

The workflow runs on the issue-tracker self-hosted runner labeled `issue-tracker` and `local-dev`. The runner acts as an orchestrator and SSHes into the current dev host, UAT host, and downstream dev host; Docker does not need to be installed inside the runner LXC.

Runner-local SSH prerequisites:

- The runner's existing `github` user SSH configuration can connect non-interactively to `akun@192.168.10.20`, `akun@192.168.10.18`, and `akun@192.168.10.8`.
- Do not write issue-tracker-specific keys or config into `/home/github/.ssh/config`; that user is shared by other local repo runners.

Target host prerequisites:

- Docker and Docker Compose plugin installed.
- `akun` can run Docker commands.
- SSH accepts the key stored in `LOCAL_DEPLOY_SSH_KEY`.
- Port `8000` is reachable from the runner and from the browser used for UAT.

The workflow copies the checked-out source tree over SSH using `deployment/scripts/remote-compose-deploy.sh`. It excludes `.git`, local caches, `exports/`, and `backups/`; no local database dumps, generated backups, `.env` files, or credentials are copied. Each deployment lands under:

```text
/home/akun/issue-tracker/releases/<sha>-<timestamp>/
/home/akun/issue-tracker/current -> releases/<sha>-<timestamp>/
```

Pre-migration database dumps are written on the target host under:

```text
/home/akun/issue-tracker/backups/<sha>-<timestamp>/pre-migration.dump
```

Run it from GitHub Actions with:

- `uat_host`: `192.168.10.18`
- `dev_host`: `192.168.10.8`
- `deploy_user`: `akun`
- `deploy_path`: `/home/akun/issue-tracker`
- `promote_dev`: `false` for UAT-only, `true` to promote after UAT passes

The remote app URLs are:

```text
http://192.168.10.18:8000
http://192.168.10.8:8000
```
