---
name: schema-change
description: Use when changing `src/issue_tracker/domain/models.py`, adding or editing an Alembic revision under `migrations/versions/`, changing DB constraints/indexes, or any data transform. Covers IT-3 (models and migrations agree, empty-Postgres upgrade, drift check) and forward-only release safety.
---

# Schema Change (IT-3)

## Steps

1. Change the model and write the revision together. Name it `NNNN_snake_name.py` (next number
   after the current head), `revision` = filename stem, `down_revision` = current head. Hand-write
   it; autogenerate only as a draft to compare against.
2. Data-preserving only: add nullable → backfill → tighten. Any drop/rename/truncate of existing
   data needs a user-approved disposition recorded in the issue before it is written.
3. Write `downgrade()` for local use, but releases never run it.
4. Add/adjust service tests for the invariant the column enforces (`tracker-invariants`).

## Verify on real Postgres (unit tests can't — they use `create_all` on SQLite)

Compose path (local): `docker compose -f deployment/docker-compose.local.yml run --rm app alembic upgrade head`.

Throwaway cloud container (Postgres 16 is installed, server stopped):

```bash
pg_ctlcluster 16 main start
su postgres -c "psql -qc \"CREATE ROLE it LOGIN PASSWORD 'it'\" -c 'CREATE DATABASE it_mig OWNER it' -c 'CREATE DATABASE it_test OWNER it'"
export PG=postgresql+psycopg://it:it@localhost:5432
DATABASE_URL=$PG/it_mig alembic upgrade head
DATABASE_URL=$PG/it_mig python .claude/skills/schema-change/schema_drift.py
TEST_DATABASE_URL=$PG/it_test python -m pytest -q tests   # needs a DB alembic has NOT touched
```

Pass = upgrade succeeds on an empty DB, drift output shows **no new differences** caused by your
change, tests pass on Postgres. Report the drift count before/after.

## Known baseline drift (2026-10-20, head `0003_guidance_audit_events`)

`schema_drift.py` reports 20 differences on `main`:
- 8 `remove_table`: `guidance_*` tables created by 0002/0003 have no models.
- 12 `modify_nullable`: FK columns (`issues.project_id`, `issue_dependencies.*`, `categories.project_id`,
  `issue_events.issue_id`, `issue_log_entries.project_id`, ...) are nullable in migrations but
  `NOT NULL` in models.

Fixing this is its own issue (tighten via a new revision after checking for NULL rows); don't fold
it into unrelated work, and don't add to it.
