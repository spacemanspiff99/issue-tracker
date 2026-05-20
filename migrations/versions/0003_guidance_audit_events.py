"""guidance audit and event ingestion

Revision ID: 0003_guidance_audit_events
Revises: 0002_guidance_sync
Create Date: 2026-05-16 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_guidance_audit_events"
down_revision = "0002_guidance_sync"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "guidance_audit_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE")),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("actor", sa.String(length=160)),
        sa.Column("related_type", sa.String(length=80)),
        sa.Column("related_id", sa.Integer()),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "guidance_ingested_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE")),
        sa.Column("repo", sa.String(length=240), nullable=False),
        sa.Column("branch", sa.String(length=160), nullable=False),
        sa.Column("commit_sha", sa.String(length=80), nullable=False),
        sa.Column("path_set_hash", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "project_id",
            "repo",
            "branch",
            "commit_sha",
            "path_set_hash",
            name="uq_guidance_event_dedupe",
        ),
    )


def downgrade() -> None:
    op.drop_table("guidance_ingested_events")
    op.drop_table("guidance_audit_entries")
