"""reconcile schema drift with models

Drops the unused guidance_* tables from 0002/0003 (no models, not in MVP scope) and tightens
foreign-key columns to NOT NULL to match the models. Refuses to run if any guidance table holds
rows or any column to tighten holds NULLs, so no data is discarded.

Revision ID: 0004_reconcile_schema_drift
Revises: 0003_guidance_audit_events
Create Date: 2026-10-20 00:00:00.000000
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "0004_reconcile_schema_drift"
down_revision = "0003_guidance_audit_events"
branch_labels = None
depends_on = None

# Child tables first so drops respect foreign keys.
GUIDANCE_TABLES = [
    "guidance_ingested_events",
    "guidance_audit_entries",
    "guidance_sync_runs",
    "guidance_sync_proposals",
    "guidance_drifts",
    "guidance_snapshots",
    "guidance_branches",
    "guidance_sources",
]

NOT_NULL_COLUMNS = [
    ("categories", "project_id"),
    ("issue_dependencies", "project_id"),
    ("issue_dependencies", "blocker_issue_id"),
    ("issue_dependencies", "blocked_issue_id"),
    ("issue_events", "issue_id"),
    ("issue_log_entries", "project_id"),
    ("issues", "project_id"),
    ("project_settings", "project_id"),
    ("sprint_issues", "sprint_id"),
    ("sprint_issues", "issue_id"),
    ("sprint_tasks", "sprint_id"),
    ("sprints", "project_id"),
]


def upgrade() -> None:
    conn = op.get_bind()
    for table in GUIDANCE_TABLES:
        rows = conn.execute(sa.text(f"SELECT count(*) FROM {table}")).scalar_one()
        if rows:
            raise RuntimeError(f"{table} has {rows} row(s); back up and resolve before dropping")
    for table, column in NOT_NULL_COLUMNS:
        nulls = conn.execute(sa.text(f"SELECT count(*) FROM {table} WHERE {column} IS NULL")).scalar_one()
        if nulls:
            raise RuntimeError(f"{table}.{column} has {nulls} NULL row(s); resolve before tightening")

    for table in GUIDANCE_TABLES:
        op.drop_table(table)
    for table, column in NOT_NULL_COLUMNS:
        op.alter_column(table, column, existing_type=sa.Integer(), nullable=False)


def downgrade() -> None:
    # Local use only; releases never downgrade. Recreates the (empty) guidance tables from the
    # revisions that originally created them.
    for table, column in NOT_NULL_COLUMNS:
        op.alter_column(table, column, existing_type=sa.Integer(), nullable=True)
    here = Path(__file__).parent
    for name in ("0002_guidance_sync", "0003_guidance_audit_events"):
        spec = importlib.util.spec_from_file_location(name, here / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.upgrade()
