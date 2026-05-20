"""guidance sync schema

Revision ID: 0002_guidance_sync
Revises: 0001_initial
Create Date: 2026-05-16 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_guidance_sync"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "guidance_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE")),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("repo_url", sa.String(length=500), nullable=False),
        sa.Column("default_branch", sa.String(length=120), nullable=False),
        sa.Column("vibecoding_target_path", sa.String(length=500)),
        sa.Column("tracked_paths", sa.JSON(), nullable=False),
        sa.Column("scan_status", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("project_id", "name", name="uq_guidance_sources_project_name"),
    )
    op.create_table(
        "guidance_branches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("guidance_sources.id", ondelete="CASCADE")),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("commit_sha", sa.String(length=80)),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("scan_status", sa.String(length=80), nullable=False),
        sa.Column("scanned_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("source_id", "name", name="uq_guidance_branches_source_name"),
    )
    op.create_table(
        "guidance_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("guidance_sources.id", ondelete="CASCADE")),
        sa.Column("branch_name", sa.String(length=160), nullable=False),
        sa.Column("commit_sha", sa.String(length=80)),
        sa.Column("path", sa.String(length=600), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("scan_status", sa.String(length=80), nullable=False),
        sa.Column("actor", sa.String(length=160)),
        sa.Column("scanned_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("source_id", "branch_name", "path", "content_hash", name="uq_guidance_snapshot_hash"),
    )
    op.create_table(
        "guidance_drifts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE")),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("guidance_sources.id", ondelete="CASCADE")),
        sa.Column("left_snapshot_id", sa.Integer(), sa.ForeignKey("guidance_snapshots.id", ondelete="SET NULL")),
        sa.Column("right_snapshot_id", sa.Integer(), sa.ForeignKey("guidance_snapshots.id", ondelete="SET NULL")),
        sa.Column("path", sa.String(length=600), nullable=False),
        sa.Column("drift_type", sa.String(length=80), nullable=False),
        sa.Column("severity", sa.String(length=40), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("recommended_action", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "guidance_sync_proposals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE")),
        sa.Column("drift_id", sa.Integer(), sa.ForeignKey("guidance_drifts.id", ondelete="SET NULL")),
        sa.Column("issue_id", sa.Integer(), sa.ForeignKey("issues.id", ondelete="SET NULL")),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("owner", sa.String(length=160)),
        sa.Column("verification_command", sa.Text()),
        sa.Column("approval_text", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "guidance_sync_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE")),
        sa.Column("proposal_id", sa.Integer(), sa.ForeignKey("guidance_sync_proposals.id", ondelete="SET NULL")),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("logs", sa.Text()),
        sa.Column("pr_url", sa.String(length=500)),
        sa.Column("branch_name", sa.String(length=240)),
        sa.Column("commit_sha", sa.String(length=80)),
        sa.Column("verification_status", sa.String(length=80)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    for table in [
        "guidance_sync_runs",
        "guidance_sync_proposals",
        "guidance_drifts",
        "guidance_snapshots",
        "guidance_branches",
        "guidance_sources",
    ]:
        op.drop_table(table)
