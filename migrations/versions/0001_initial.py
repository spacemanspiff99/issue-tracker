"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-14 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

issue_status = sa.Enum(
    "BACKLOG", "IN_PROGRESS", "DONE", name="issuestatus", native_enum=False, create_constraint=True
)
sprint_status = sa.Enum(
    "PLANNED", "ACTIVE", "CLOSED", name="sprintstatus", native_enum=False, create_constraint=True
)
task_status = sa.Enum(
    "TODO", "IN_PROGRESS", "DONE", name="taskstatus", native_enum=False, create_constraint=True
)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("repo_url", sa.String(length=500)),
        sa.Column("default_branch", sa.String(length=80), nullable=False),
        sa.Column("tracker_path_hint", sa.String(length=500)),
        sa.Column("rules_path_hint", sa.String(length=500)),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("next_sequence", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.UniqueConstraint("key"),
    )
    op.create_table(
        "project_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE")),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.UniqueConstraint("project_id", "key", name="uq_project_settings_key"),
    )
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE")),
        sa.Column("key", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("checklist", sa.Text(), nullable=False),
        sa.UniqueConstraint("project_id", "key", name="uq_categories_project_key"),
    )
    op.create_table(
        "issues",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE")),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=220), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("status", issue_status, nullable=False),
        sa.Column("priority", sa.String(length=40), nullable=False),
        sa.Column("labels", sa.JSON(), nullable=False),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id", ondelete="SET NULL")),
        sa.Column("summary", sa.Text()),
        sa.Column("proposed_approach", sa.Text()),
        sa.Column("acceptance_criteria", sa.Text(), nullable=False),
        sa.Column("originating_llm", sa.String(length=120)),
        sa.Column("closed_by", sa.String(length=120)),
        sa.Column("close_note", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("sequence > 0", name="ck_issues_positive_sequence"),
        sa.UniqueConstraint("project_id", "sequence", name="uq_issues_project_sequence"),
        sa.UniqueConstraint("project_id", "slug", name="uq_issues_project_slug"),
    )
    op.create_table(
        "sprints",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE")),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=220), nullable=False),
        sa.Column("goal", sa.String(length=240), nullable=False),
        sa.Column("context", sa.Text()),
        sa.Column("status", sprint_status, nullable=False),
        sa.Column("next_sprint_id", sa.Integer(), sa.ForeignKey("sprints.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("sequence > 0", name="ck_sprints_positive_sequence"),
        sa.UniqueConstraint("project_id", "sequence", name="uq_sprints_project_sequence"),
        sa.UniqueConstraint("project_id", "slug", name="uq_sprints_project_slug"),
    )
    op.create_table(
        "issue_dependencies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE")),
        sa.Column("blocker_issue_id", sa.Integer(), sa.ForeignKey("issues.id", ondelete="CASCADE")),
        sa.Column("blocked_issue_id", sa.Integer(), sa.ForeignKey("issues.id", ondelete="CASCADE")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("blocker_issue_id <> blocked_issue_id", name="ck_issue_dependency_not_self"),
        sa.UniqueConstraint("blocker_issue_id", "blocked_issue_id", name="uq_issue_dependency_edge"),
    )
    op.create_table(
        "issue_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("issue_id", sa.Integer(), sa.ForeignKey("issues.id", ondelete="CASCADE")),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("actor", sa.String(length=120)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "sprint_issues",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sprint_id", sa.Integer(), sa.ForeignKey("sprints.id", ondelete="CASCADE")),
        sa.Column("issue_id", sa.Integer(), sa.ForeignKey("issues.id", ondelete="CASCADE")),
        sa.Column("phase", sa.String(length=80)),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("status", task_status, nullable=False),
        sa.UniqueConstraint("sprint_id", "issue_id", name="uq_sprint_issues"),
    )
    op.create_table(
        "sprint_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sprint_id", sa.Integer(), sa.ForeignKey("sprints.id", ondelete="CASCADE")),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("model", sa.String(length=120)),
        sa.Column("phase", sa.String(length=80)),
        sa.Column("file_slug", sa.String(length=220)),
        sa.Column("status", task_status, nullable=False),
        sa.Column("parallel_group", sa.String(length=80)),
        sa.Column("stop_handoff", sa.Text()),
    )
    op.create_table(
        "linked_prs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("issue_id", sa.Integer(), sa.ForeignKey("issues.id", ondelete="CASCADE")),
        sa.Column("sprint_id", sa.Integer(), sa.ForeignKey("sprints.id", ondelete="CASCADE")),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("repo", sa.String(length=240), nullable=False),
        sa.Column("pr_number", sa.Integer()),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("merge_status", sa.String(length=80)),
    )
    op.create_table(
        "issue_log_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE")),
        sa.Column("issue_id", sa.Integer(), sa.ForeignKey("issues.id", ondelete="SET NULL")),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id", ondelete="SET NULL")),
        sa.Column("root_cause", sa.Text(), nullable=False),
        sa.Column("prevention_added", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    for table in [
        "issue_log_entries",
        "linked_prs",
        "sprint_tasks",
        "sprint_issues",
        "issue_events",
        "issue_dependencies",
        "sprints",
        "issues",
        "categories",
        "project_settings",
        "app_settings",
        "projects",
        "users",
    ]:
        op.drop_table(table)
