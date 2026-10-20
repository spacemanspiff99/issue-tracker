# Issue 0013: Reconcile Schema Drift Before Production Data

Status: backlog
Recommended model: claude-opus-5-5 high
Category gates: `IT-3`
Sprint: Sprint 0007

## Problem

`.claude/skills/schema-change/schema_drift.py` reports 20 differences after `alembic upgrade head` on an empty Postgres: 8 `guidance_*` tables from `0002`/`0003` have no models, and 12 foreign-key columns are nullable in migrations but `NOT NULL` in models. Unit tests use `create_all`, so they never see this. It must be fixed before production (`192.168.10.8`) holds real data.

## Scope

- Decide the `guidance_*` tables: add models (if the guidance-sync feature is in v1) or drop them in a new revision (if not). Default: drop — not in `MVP_SCOPE_LOCK.md`.
- New revision `0004_*` tightening the 12 FK columns to `NOT NULL` (check for NULL rows first).

## Acceptance Criteria

- [ ] `alembic upgrade head` on an empty Postgres succeeds.
- [ ] `schema_drift.py` reports 0 differences.
- [ ] `TEST_DATABASE_URL=<fresh postgres> python -m pytest tests` passes.
- [ ] CI runs the migration + drift check against a Postgres service so drift can't return.

## Category Checklists

`IT-3` Schema And Migration Safety: Verify SQLAlchemy models, PostgreSQL constraints, and Alembic migrations agree; run migration checks on an empty database.

## Verification Commands

See `.claude/skills/schema-change/SKILL.md` (Verify on real Postgres).

## STOP

Stop when the drift check is 0 locally and in CI, or record which difference cannot be reconciled and why.
