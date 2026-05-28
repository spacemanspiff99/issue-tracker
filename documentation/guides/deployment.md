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

UAT source-of-truth rule:

- "Deploy to UAT" means deploy the intended current dev code after it has been committed and pushed.
- Before dispatching the workflow, check the dev checkout with `git status --short`, identify the current branch and `HEAD` SHA, and compare that SHA with the remote ref that GitHub Actions will check out.
- If local product, UI, schema, deployment, or documentation changes are uncommitted, do not deploy yet unless the operator explicitly chooses to deploy a named older SHA.
- Record the exact branch and SHA in the deployment notes or PR comment.
- Code deployment preserves the existing UAT database by default. It must not reset UAT volumes, drop/recreate the UAT database, or overwrite UAT data with dev data.
- Code deployment does not copy the dev database. If UAT should contain dev data, run a separate backup-first data restore plan and record that data movement explicitly.
- A plan, sprint, or checklist that describes a UAT refresh is not approval to execute it. Before overwriting UAT, stop and require the operator to reply with `CONFIRM OVERWRITE uat`.

Production data rules:

- Production deploys preserve the existing production database by default.
- Production deploys run only reviewed forward Alembic migrations after a successful pre-migration backup.
- Production deploys must not reset volumes, drop/recreate databases, truncate tables, downgrade migrations, or restore data unless the user explicitly requests a production restore from a named backup.
- Never copy dev or UAT data upward into production.

Production-to-lower-environment refresh:

- Copying production data down to UAT or dev for realistic testing is useful, but it is a separate data refresh operation, not a deploy.
- A refresh must name source `prod` and target `uat` or `dev`, and must explicitly confirm that the target database will be overwritten.
- Required confirmation phrase before overwrite: `CONFIRM OVERWRITE <target>`, where `<target>` is `uat` or `dev`.
- Generic continuation messages such as `ok`, `continue`, `ssh key setup`, `credentials ready`, or `try again` only resolve the immediate blocker. They do not authorize a later restore, deploy, workflow dispatch, volume reset, or other target mutation.
- Before overwriting the target, take a target backup and record the source backup or dump identity used for the refresh.
- Production remains read-only for the refresh except for taking a dump or backup.
- Document secret, password-hash, session, token, and environment-value handling before refresh. Do not copy production `.env` files or secrets to UAT/dev.
- After restore, run Alembic, `/health`, MCP smoke, and route/browser checks against the target.

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
- `expected_deploy_sha`: the exact committed SHA the operator intends to deploy

Dispatch example for a UAT-only deployment:

```bash
git status --short --branch
git rev-parse HEAD
git rev-parse @{u}
gh workflow run local-pipeline.yml --ref <branch-or-sha> \
  -f expected_deploy_sha=<exact-committed-sha> \
  -f uat_host=192.168.10.26 \
  -f prod_host=192.168.10.27 \
  -f deploy_user=akun \
  -f deploy_path=/home/akun/issue-tracker \
  -f prod_env_file=/home/akun/issue-tracker/prod.env \
  -f deploy_prod=false
```

The workflow prints `GITHUB_REF` and `GITHUB_SHA` and refuses to deploy unless `GITHUB_SHA` exactly matches `expected_deploy_sha`. This protects against accidentally dispatching a branch tip other than the commit that was reviewed locally. It does not make uncommitted files available to GitHub Actions; uncommitted local changes still block "deploy current dev" until they are committed and pushed, unless the operator explicitly chooses an older SHA.

The deploy script enforces environment-specific host checks:

- UAT refuses to deploy unless `TARGET_HOST` is `192.168.10.26` and the remote hostname is `app-uat`.
- Production refuses to deploy unless `TARGET_HOST` is `192.168.10.27`, the remote hostname is `app-prod`, `REMOTE_ENV_FILE` exists, and `APP_SECRET_KEY`, `DATABASE_URL`, and `POSTGRES_PASSWORD` are provided by that file.
- Production refuses `SKIP_DB_BACKUP=1`.

The remote app URLs are:

```text
http://192.168.10.26:8000
http://192.168.10.27:8000
```

Observability follow-up:

- Application containers emit structured stderr logs with stable `app`, `service`, `source`, and
  `environment` fields. `APP_ENVIRONMENT` must be set to `dev`, `uat`, or `production` in the
  relevant environment file before those logs are used for dashboards.
- Uvicorn access logging is disabled in container startup; use the application `http_request`
  summary logs instead so query strings, request bodies, cookies, and raw IDs are not collected.
- Container log shipping gaps are tracked in `documentation/issues/0013-container-logging-loki-labels.md`.
- Do not treat UAT or production logging as complete until Loki queries from the monitoring host show issue-tracker `app` and `postgres` streams for dev, UAT, and production with stable environment labels.

## Local Docker Preflight Isolation

When running checks from a temporary worktree on the dev host, do not use the default Compose identity. The live dev stack may already own the default project name, fixed PostgreSQL container name, host port, and volume.

Before building, check host and Docker capacity:

```bash
df -h / /tmp
docker system df
```

Playwright browser dependencies are container dependencies. The app image may install Chromium and required Linux libraries during `docker compose build`; do not install Playwright browser dependencies on the dev host from an agent session. If browser UAT cannot run because dependencies are missing, rebuild the app image or run the test inside the app container.

Use a distinct project name, PostgreSQL container name, and host port for isolated preflight:

```bash
COMPOSE_PROJECT_NAME=issue_tracker_preflight \
POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres \
APP_HTTP_PORT=18000 \
docker compose -f deployment/docker-compose.local.yml config

COMPOSE_PROJECT_NAME=issue_tracker_preflight \
POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres \
APP_HTTP_PORT=18000 \
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/
```

Before and after preflight on the dev host, confirm the live dev app remains healthy:

```bash
curl -fsS http://192.168.10.20:8000/health
```

Do not run `docker compose up`, `down`, or `rm` against the default project from a temporary worktree unless the user explicitly asks to restart dev.

After isolated preflight, clean up temporary resources before closeout:

```bash
COMPOSE_PROJECT_NAME=issue_tracker_preflight \
POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres \
APP_HTTP_PORT=18000 \
docker compose -f deployment/docker-compose.local.yml down -v

docker image rm issue_tracker_preflight-app
docker builder prune
docker system df
```

The `down -v` command is only for the disposable preflight project named above. Do not remove the default dev project, production or UAT containers, or any named volume that may contain tracker data unless that exact target is explicitly confirmed. Prefer targeted image removal and builder-cache cleanup before broad Docker pruning.

## Production-To-UAT Or Dev Data Refresh

Data refresh is separate from deployment. It is destructive to the target environment and non-destructive to production.

Required plan before execution:

- Source must be `prod`.
- Target must be either `uat` or `dev`; never target production.
- The user must explicitly confirm the target overwrite with `CONFIRM OVERWRITE <target>`.
- Production may only be read for `pg_dump` or an equivalent backup operation.
- Take and verify a target backup before overwrite.
- Record the production dump identity, target backup path, target host, target database name, operator, date, and post-restore commit SHA.
- Do not copy production `.env`, secrets, tokens, runtime config, SSH keys, or certificates to lower environments.
- Treat sessions, password hashes, API tokens, and remembered login state as sensitive. Until the app has an automated sanitizer, expire sessions and perform target-only admin setup or password reset after restore.
- After restore, run `alembic upgrade head`, `/health`, MCP smoke, route checks, and browser or manual UAT against the target.

Never copy dev or UAT data upward into production. Production restores require a separate explicit request naming the production backup to restore.
