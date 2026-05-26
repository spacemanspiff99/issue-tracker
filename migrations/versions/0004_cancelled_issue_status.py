"""add cancelled issue status

Revision ID: 0004_cancelled_issue_status
Revises: 0003_guidance_audit_events
Create Date: 2026-05-24 00:00:00.000000
"""

from __future__ import annotations

from alembic import op

revision = "0004_cancelled_issue_status"
down_revision = "0003_guidance_audit_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE issues DROP CONSTRAINT IF EXISTS issuestatus")
    op.create_check_constraint(
        "issuestatus",
        "issues",
        "status IN ('BACKLOG', 'IN_PROGRESS', 'DONE', 'CANCELLED')",
    )


def downgrade() -> None:
    op.execute("UPDATE issues SET status = 'BACKLOG' WHERE status = 'CANCELLED'")
    op.execute("ALTER TABLE issues DROP CONSTRAINT IF EXISTS issuestatus")
    op.create_check_constraint(
        "issuestatus",
        "issues",
        "status IN ('BACKLOG', 'IN_PROGRESS', 'DONE')",
    )
