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

## Local Runner UAT -> Production Pipeline

Use `.github/workflows/local-pipeline.yml` for the local network pipeline:

1. Deploy the checked-out source tree to UAT at `akun@app-uat` / `192.168.10.26`.
2. Verify UAT with Docker build, pre-migration backup, Alembic, tests, ruff, `/health`, MCP smoke, and browser UAT.
3. Optionally deploy the same revision to production at `akun@app-prod` / `192.168.10.27` after UAT passes.
4. Verify production with pre-migration backup, Alembic, `/health`, and MCP smoke.

The workflow runs on the issue-tracker self-hosted runner labeled `issue-tracker` and `local-dev`. The runner is container `113`, hostname `github-runner`. It acts as an orchestrator and SSHes into the UAT and production app hosts; Docker does not need to be installed inside the runner LXC.

Runner-local SSH prerequisites:

- The runner's existing `github` user SSH configuration can connect non-interactively to `akun@192.168.10.26` and `akun@192.168.10.27`.
- Do not write issue-tracker-specific keys or config into `/home/github/.ssh/config`; that user is shared by other local repo runners.

Target host prerequisites:

- UAT host is VM `114`, hostname `app-uat`, IP `192.168.10.26`.
- Production host is VM `119`, hostname `app-prod`, IP `192.168.10.27`.
- Docker and Docker Compose plugin installed.
- `akun` can run Docker commands.
- SSH accepts the key stored in `LOCAL_DEPLOY_SSH_KEY`.
- Port `8000` is reachable from the runner and from the browser used for UAT or production smoke checks.
- `/home/akun/issue-tracker` exists and is writable by `akun`.

Production configuration prerequisite:

- Production must provide a separate uncommitted env file on `app-prod`, defaulting to `/home/akun/issue-tracker/prod.env`.
- The prod env file must provide production values for `APP_SECRET_KEY`, `DATABASE_URL`, and `POSTGRES_PASSWORD`; set `POSTGRES_DB` and `POSTGRES_USER` there too if production does not use the defaults.
- Do not copy the UAT env file to prod. Do not commit prod env values to Git.

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

- `uat_host`: `192.168.10.26`
- `prod_host`: `192.168.10.27`
- `deploy_user`: `akun`
- `deploy_path`: `/home/akun/issue-tracker`
- `prod_env_file`: `/home/akun/issue-tracker/prod.env`
- `deploy_prod`: `false` for UAT-only, `true` to deploy production after UAT passes

The deploy script enforces environment-specific host checks:

- UAT refuses to deploy unless `TARGET_HOST` is `192.168.10.26` and the remote hostname is `app-uat`.
- Production refuses to deploy unless `TARGET_HOST` is `192.168.10.27`, the remote hostname is `app-prod`, `REMOTE_ENV_FILE` exists, and `APP_SECRET_KEY`, `DATABASE_URL`, and `POSTGRES_PASSWORD` are provided by that file.
- Production refuses `SKIP_DB_BACKUP=1`.

The remote app URLs are:

```text
http://192.168.10.26:8000
http://192.168.10.27:8000
```
