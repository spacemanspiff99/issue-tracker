# Issue 0008: Local Runtime Gate For Manual UAT

Status: backlog
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

- [ ] `docker compose -f deployment/docker-compose.local.yml build` completes without host Python setup.
- [ ] `docker compose -f deployment/docker-compose.local.yml run --rm app alembic upgrade head` succeeds against local PostgreSQL.
- [ ] `docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/` passes.
- [ ] `docker compose -f deployment/docker-compose.local.yml up` starts app and PostgreSQL.
- [ ] `GET /health` returns app readiness and database connectivity.
- [ ] No `.env`, logs, database dumps, backups, generated exports, or local credentials are committed.

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
