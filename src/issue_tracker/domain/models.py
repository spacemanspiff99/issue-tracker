from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from issue_tracker.domain.enums import IssueStatus, SprintStatus, TaskStatus


class Base(DeclarativeBase):
    type_annotation_map = {dict[str, object]: JSON()}


def now_column() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = now_column()


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    repo_url: Mapped[str | None] = mapped_column(String(500))
    default_branch: Mapped[str] = mapped_column(String(80), default="main", nullable=False)
    tracker_path_hint: Mapped[str | None] = mapped_column(String(500))
    rules_path_hint: Mapped[str | None] = mapped_column(String(500))
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    next_sequence: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = now_column()

    categories: Mapped[list[Category]] = relationship(back_populates="project", cascade="all, delete")
    issues: Mapped[list[Issue]] = relationship(back_populates="project", cascade="all, delete")
    sprints: Mapped[list[Sprint]] = relationship(back_populates="project", cascade="all, delete")


class ProjectSetting(Base):
    __tablename__ = "project_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    key: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (UniqueConstraint("project_id", "key", name="uq_project_settings_key"),)


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    key: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    checklist: Mapped[str] = mapped_column(Text, nullable=False)

    project: Mapped[Project] = relationship(back_populates="categories")
    issues: Mapped[list[Issue]] = relationship(back_populates="category")

    __table_args__ = (UniqueConstraint("project_id", "key", name="uq_categories_project_key"),)


class Issue(Base):
    __tablename__ = "issues"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    slug: Mapped[str] = mapped_column(String(220), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    status: Mapped[IssueStatus] = mapped_column(
        SAEnum(IssueStatus, native_enum=False, validate_strings=True, create_constraint=True),
        default=IssueStatus.BACKLOG,
        nullable=False,
    )
    priority: Mapped[str] = mapped_column(String(40), default="normal", nullable=False)
    labels: Mapped[dict[str, object]] = mapped_column(default=dict, nullable=False)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"))
    summary: Mapped[str | None] = mapped_column(Text)
    proposed_approach: Mapped[str | None] = mapped_column(Text)
    acceptance_criteria: Mapped[str] = mapped_column(Text, nullable=False)
    originating_llm: Mapped[str | None] = mapped_column(String(120))
    closed_by: Mapped[str | None] = mapped_column(String(120))
    close_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = now_column()
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    project: Mapped[Project] = relationship(back_populates="issues")
    category: Mapped[Category | None] = relationship(back_populates="issues")

    __table_args__ = (
        UniqueConstraint("project_id", "sequence", name="uq_issues_project_sequence"),
        UniqueConstraint("project_id", "slug", name="uq_issues_project_slug"),
        CheckConstraint("sequence > 0", name="ck_issues_positive_sequence"),
    )


class IssueDependency(Base):
    __tablename__ = "issue_dependencies"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    blocker_issue_id: Mapped[int] = mapped_column(ForeignKey("issues.id", ondelete="CASCADE"))
    blocked_issue_id: Mapped[int] = mapped_column(ForeignKey("issues.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = now_column()

    blocker: Mapped[Issue] = relationship(foreign_keys=[blocker_issue_id])
    blocked: Mapped[Issue] = relationship(foreign_keys=[blocked_issue_id])

    __table_args__ = (
        UniqueConstraint("blocker_issue_id", "blocked_issue_id", name="uq_issue_dependency_edge"),
        CheckConstraint("blocker_issue_id <> blocked_issue_id", name="ck_issue_dependency_not_self"),
    )


class IssueEvent(Base):
    __tablename__ = "issue_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    issue_id: Mapped[int] = mapped_column(ForeignKey("issues.id", ondelete="CASCADE"))
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    actor: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = now_column()


class Sprint(Base):
    __tablename__ = "sprints"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    slug: Mapped[str] = mapped_column(String(220), nullable=False)
    goal: Mapped[str] = mapped_column(String(240), nullable=False)
    context: Mapped[str | None] = mapped_column(Text)
    status: Mapped[SprintStatus] = mapped_column(
        SAEnum(SprintStatus, native_enum=False, validate_strings=True, create_constraint=True),
        default=SprintStatus.PLANNED,
        nullable=False,
    )
    next_sprint_id: Mapped[int | None] = mapped_column(ForeignKey("sprints.id"))
    created_at: Mapped[datetime] = now_column()
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    project: Mapped[Project] = relationship(back_populates="sprints")
    issues: Mapped[list[SprintIssue]] = relationship(back_populates="sprint", cascade="all, delete")

    __table_args__ = (
        UniqueConstraint("project_id", "sequence", name="uq_sprints_project_sequence"),
        UniqueConstraint("project_id", "slug", name="uq_sprints_project_slug"),
        CheckConstraint("sequence > 0", name="ck_sprints_positive_sequence"),
    )


class SprintIssue(Base):
    __tablename__ = "sprint_issues"

    id: Mapped[int] = mapped_column(primary_key=True)
    sprint_id: Mapped[int] = mapped_column(ForeignKey("sprints.id", ondelete="CASCADE"))
    issue_id: Mapped[int] = mapped_column(ForeignKey("issues.id", ondelete="CASCADE"))
    phase: Mapped[str | None] = mapped_column(String(80))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[TaskStatus] = mapped_column(
        SAEnum(TaskStatus, native_enum=False, validate_strings=True, create_constraint=True),
        default=TaskStatus.TODO,
        nullable=False,
    )

    sprint: Mapped[Sprint] = relationship(back_populates="issues")
    issue: Mapped[Issue] = relationship()

    __table_args__ = (UniqueConstraint("sprint_id", "issue_id", name="uq_sprint_issues"),)


class SprintTask(Base):
    __tablename__ = "sprint_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    sprint_id: Mapped[int] = mapped_column(ForeignKey("sprints.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    model: Mapped[str | None] = mapped_column(String(120))
    phase: Mapped[str | None] = mapped_column(String(80))
    file_slug: Mapped[str | None] = mapped_column(String(220))
    status: Mapped[TaskStatus] = mapped_column(
        SAEnum(TaskStatus, native_enum=False, validate_strings=True, create_constraint=True),
        default=TaskStatus.TODO,
        nullable=False,
    )
    parallel_group: Mapped[str | None] = mapped_column(String(80))
    stop_handoff: Mapped[str | None] = mapped_column(Text)


class LinkedPR(Base):
    __tablename__ = "linked_prs"

    id: Mapped[int] = mapped_column(primary_key=True)
    issue_id: Mapped[int | None] = mapped_column(ForeignKey("issues.id", ondelete="CASCADE"))
    sprint_id: Mapped[int | None] = mapped_column(ForeignKey("sprints.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String(80), default="github", nullable=False)
    repo: Mapped[str] = mapped_column(String(240), nullable=False)
    pr_number: Mapped[int | None] = mapped_column(Integer)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    merge_status: Mapped[str | None] = mapped_column(String(80))


class IssueLogEntry(Base):
    __tablename__ = "issue_log_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    issue_id: Mapped[int | None] = mapped_column(ForeignKey("issues.id", ondelete="SET NULL"))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"))
    root_cause: Mapped[str] = mapped_column(Text, nullable=False)
    prevention_added: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = now_column()


class GuidanceSource(Base):
    __tablename__ = "guidance_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    repo_url: Mapped[str] = mapped_column(String(500), nullable=False)
    default_branch: Mapped[str] = mapped_column(String(120), default="main", nullable=False)
    vibecoding_target_path: Mapped[str | None] = mapped_column(String(500))
    tracked_paths: Mapped[dict[str, object]] = mapped_column(default=dict, nullable=False)
    scan_status: Mapped[str] = mapped_column(String(80), default="not-scanned", nullable=False)
    created_at: Mapped[datetime] = now_column()

    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_guidance_sources_project_name"),)


class GuidanceBranch(Base):
    __tablename__ = "guidance_branches"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("guidance_sources.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    commit_sha: Mapped[str | None] = mapped_column(String(80))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    scan_status: Mapped[str] = mapped_column(String(80), default="not-scanned", nullable=False)
    scanned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (UniqueConstraint("source_id", "name", name="uq_guidance_branches_source_name"),)


class GuidanceSnapshot(Base):
    __tablename__ = "guidance_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("guidance_sources.id", ondelete="CASCADE"))
    branch_name: Mapped[str] = mapped_column(String(160), nullable=False)
    commit_sha: Mapped[str | None] = mapped_column(String(80))
    path: Mapped[str] = mapped_column(String(600), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    scan_status: Mapped[str] = mapped_column(String(80), default="ok", nullable=False)
    actor: Mapped[str | None] = mapped_column(String(160))
    scanned_at: Mapped[datetime] = now_column()

    __table_args__ = (
        UniqueConstraint("source_id", "branch_name", "path", "content_hash", name="uq_guidance_snapshot_hash"),
    )


class GuidanceDrift(Base):
    __tablename__ = "guidance_drifts"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    source_id: Mapped[int | None] = mapped_column(ForeignKey("guidance_sources.id", ondelete="CASCADE"))
    left_snapshot_id: Mapped[int | None] = mapped_column(ForeignKey("guidance_snapshots.id", ondelete="SET NULL"))
    right_snapshot_id: Mapped[int | None] = mapped_column(ForeignKey("guidance_snapshots.id", ondelete="SET NULL"))
    path: Mapped[str] = mapped_column(String(600), nullable=False)
    drift_type: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[str] = mapped_column(String(40), default="normal", nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_action: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(80), default="open", nullable=False)
    created_at: Mapped[datetime] = now_column()


class GuidanceSyncProposal(Base):
    __tablename__ = "guidance_sync_proposals"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    drift_id: Mapped[int | None] = mapped_column(ForeignKey("guidance_drifts.id", ondelete="SET NULL"))
    issue_id: Mapped[int | None] = mapped_column(ForeignKey("issues.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(80), default="draft", nullable=False)
    owner: Mapped[str | None] = mapped_column(String(160))
    verification_command: Mapped[str | None] = mapped_column(Text)
    approval_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = now_column()


class GuidanceSyncRun(Base):
    __tablename__ = "guidance_sync_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    proposal_id: Mapped[int | None] = mapped_column(ForeignKey("guidance_sync_proposals.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(80), nullable=False)
    logs: Mapped[str | None] = mapped_column(Text)
    pr_url: Mapped[str | None] = mapped_column(String(500))
    branch_name: Mapped[str | None] = mapped_column(String(240))
    commit_sha: Mapped[str | None] = mapped_column(String(80))
    verification_status: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = now_column()


class GuidanceAuditEntry(Base):
    __tablename__ = "guidance_audit_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    actor: Mapped[str | None] = mapped_column(String(160))
    related_type: Mapped[str | None] = mapped_column(String(80))
    related_id: Mapped[int | None] = mapped_column(Integer)
    details: Mapped[dict[str, object]] = mapped_column(default=dict, nullable=False)
    created_at: Mapped[datetime] = now_column()


class GuidanceIngestedEvent(Base):
    __tablename__ = "guidance_ingested_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    repo: Mapped[str] = mapped_column(String(240), nullable=False)
    branch: Mapped[str] = mapped_column(String(160), nullable=False)
    commit_sha: Mapped[str] = mapped_column(String(80), nullable=False)
    path_set_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(80), default="received", nullable=False)
    created_at: Mapped[datetime] = now_column()

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "repo",
            "branch",
            "commit_sha",
            "path_set_hash",
            name="uq_guidance_event_dedupe",
        ),
    )


class AppSetting(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
