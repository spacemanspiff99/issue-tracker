# Issue 0013: Reconcile Schema Drift Before Production Data

Status: in review (PR open, not merged)
Recommended model: claude-opus-5-5 high
Category gates: `IT-3`
Sprint: Sprint 0007

## Problem

`.claude/skills/schema-change/schema_drift.py` reports 20 differences after `alembic upgrade head` on an empty Postgres: 8 `guidance_*` tables from `0002`/`0003` have no models, and 12 foreign-key columns are nullable in migrations but `NOT NULL` in models. Unit tests use `create_all`, so they never see this. It must be fixed before production (`192.168.10.8`) holds real data.

## Scope

- Decide the `guidance_*` tables: add models (if the guidance-sync feature is in v1) or drop them in a new revision (if not). Default: drop — not in `MVP_SCOPE_LOCK.md`.
- New revision `0004_*` tightening the 12 FK columns to `NOT NULL` (check for NULL rows first).

## Acceptance Criteria

- [x] `alembic upgrade head` on an empty Postgres succeeds.
- [x] `schema_drift.py` reports 0 differences.
- [x] `TEST_DATABASE_URL=<fresh postgres> python -m pytest tests` passes.
- [x] CI runs the migration + drift check against a Postgres service so drift can't return.

## Data Disposition

- `guidance_*` (8 tables): **dropped** in `0004_reconcile_schema_drift` per this issue's default
  (guidance sync is not in `MVP_SCOPE_LOCK.md`; no model or app code reads/writes them). The
  revision counts rows first and aborts the upgrade (transaction rolled back, stays at 0003) if
  any guidance table is non-empty, so no data can be discarded. Owner approval of the drop is
  given at PR merge.
- 12 FK columns: tightened to `NOT NULL`; the revision aborts if any holds NULLs.

## Evidence (2026-10-20, local Postgres 16)

- Drift before: 20 (8 `remove_table`, 12 `modify_nullable`). After `alembic upgrade head` on an
  empty DB: `0 difference(s)`, exit 0.
- `alembic downgrade 0003_guidance_audit_events` → drift 20 again; re-upgrade → 0.
- Guard: row inserted into `guidance_audit_entries` at 0003 → upgrade raises `RuntimeError`,
  `alembic current` stays `0003_guidance_audit_events`.
- `TEST_DATABASE_URL=$PG/it_test python -m pytest -q tests` → 12 passed.
- CI: new `schema` job (Postgres 16 service: upgrade head, drift check, pytest on Postgres).

## Category Checklists

`IT-3` Schema And Migration Safety: Verify SQLAlchemy models, PostgreSQL constraints, and Alembic migrations agree; run migration checks on an empty database.

## Verification Commands

See `.claude/skills/schema-change/SKILL.md` (Verify on real Postgres).

## STOP

Stop when the drift check is 0 locally and in CI, or record which difference cannot be reconciled and why.
