# Issue 0008: Local Runtime Gate For Manual UAT

Status: done
Recommended model: GPT-5.5 high
Category gates: `IT-3`, `IT-6`
Sprint: Sprint 0007

## Problem

Manual UAT cannot start until the local Docker runtime proves it can build the app, start PostgreSQL, run explicit migrations, run tests, and serve `/health` with database connectivity.

## Scope

- Verify Docker daemon access and record the owner action if unavailable.
- Build the local app image from `deployment/docker-compose.local.yml`.
- Run `alembic upgrade head` explicitly against local PostgreSQL.
- Run the full pytest suite through the app service.
- Start the local stack and verify `/health`.
- Record exact commands and pass/fail evidence in the sprint closeout.

## Acceptance Criteria

- [x] `docker compose -f deployment/docker-compose.local.yml build` completes without host Python setup. Proven by CI `e2e` (`$COMPOSE up -d --build postgres app`, clean runner, no host Python) on `c10970f`: [run](https://github.com/spacemanspiff99/issue-tracker/actions/runs/39466799278/job/118780179039). Blocked in the cloud container only (network policy denies `deb.debian.org`).
- [x] `docker compose -f deployment/docker-compose.local.yml run --rm app alembic upgrade head` succeeds against local PostgreSQL.
- [x] `docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/` passes.
- [x] `docker compose -f deployment/docker-compose.local.yml up` starts app and PostgreSQL.
- [x] `GET /health` returns app readiness and database connectivity.
- [x] No `.env`, logs, database dumps, backups, generated exports, or local credentials are committed.

## Evidence (2026-10-20, `a98b164`, cloud container)

Full table in [UAT notes](../uat/2026-10-20-cloud-container-uat-readiness.md).

- `config -q` → exit 0.
- `build` → CI `e2e` job built and started the compose stack on `c10970f` ([run](https://github.com/spacemanspiff99/issue-tracker/actions/runs/39466799278/job/118780179039)). In the cloud container it was blocked by environment (Docker Hub 429, then apt `403` for `deb.debian.org`); image built from the same context minus the `playwright install --with-deps` line. Owner re-runs `build` as written on the LAN.
- `alembic upgrade head` on a fresh volume → `0001_initial … 0004_reconcile_schema_drift`.
- `pytest tests/` in the app container → `22 passed, 22 skipped` (e2e skipped without `RUN_BROWSER_UAT`).
- `up -d` → app + postgres running; `/health` → `{"ok":true,"database":"ok"}`.
- `RUN_BROWSER_UAT=1 pytest tests/e2e` against the stack → `22 passed`, 70 screenshots.
- `git status` after the run: only intended source/doc files; `exports/` and `artifacts/` gitignored.
- Originating model: claude-opus-5-5 (effort: low).
- In-container `ruff check .` fails on cache permissions → [0027](0027-ruff-in-app-container-cache-permission.md) (`--no-cache` passes).

## Category Checklists

`IT-3` Schema And Migration Safety: Verify SQLAlchemy models, PostgreSQL constraints, and Alembic migrations agree; run migration checks on an empty database.

`IT-6` Deployment And Configuration Drift: Verify compose files, env vars, health checks, explicit migrations, and workflow behavior stay aligned.

## Verification Commands

```bash
docker compose -f deployment/docker-compose.local.yml config
docker compose -f deployment/docker-compose.local.yml build
docker compose -f deployment/docker-compose.local.yml run --rm app alembic upgrade head
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/
docker compose -f deployment/docker-compose.local.yml up
```

## STOP

Stop when the local runtime is proven ready for browser UAT, or record the exact blocker, command output summary, owner action, and next retry step in Sprint 0007.
