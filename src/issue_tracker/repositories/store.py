from __future__ import annotations

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from issue_tracker.domain.enums import IssueStatus, SprintStatus
from issue_tracker.domain.models import (
    Category,
    Issue,
    IssueDependency,
    IssueEvent,
    IssueLogEntry,
    LinkedPR,
    Project,
    Sprint,
    SprintIssue,
    User,
)


class Repository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, obj):
        self.session.add(obj)
        return obj

    def count_users(self) -> int:
        return self.session.scalar(select(func.count(User.id))) or 0

    def get_user_by_username(self, username: str) -> User | None:
        return self.session.scalar(select(User).where(User.username == username))

    def get_project(self, project_id: int) -> Project:
        project = self.session.get(Project, project_id)
        if project is None:
            raise KeyError(f"Project {project_id} was not found")
        return project

    def list_projects(self) -> list[Project]:
        return list(self.session.scalars(select(Project).order_by(Project.name)))

    def search_projects(self, query: str) -> list[Project]:
        term = f"%{query.strip()}%"
        return list(
            self.session.scalars(
                select(Project)
                .where(
                    or_(
                        Project.name.ilike(term),
                        Project.repo_url.ilike(term),
                        Project.tracker_path_hint.ilike(term),
                        Project.rules_path_hint.ilike(term),
                    )
                )
                .order_by(Project.name)
            )
        )

    def allocate_sequence(self, project_id: int) -> int:
        stmt: Select[tuple[Project]] = select(Project).where(Project.id == project_id).with_for_update()
        project = self.session.scalar(stmt)
        if project is None:
            raise KeyError(f"Project {project_id} was not found")
        sequence = project.next_sequence
        project.next_sequence += 1
        return sequence

    def get_category(self, category_id: int | None) -> Category | None:
        return self.session.get(Category, category_id) if category_id else None

    def list_categories(self, project_id: int) -> list[Category]:
        return list(
            self.session.scalars(
                select(Category).where(Category.project_id == project_id).order_by(Category.key)
            )
        )

    def get_issue(self, issue_id: int) -> Issue:
        issue = self.session.get(Issue, issue_id)
        if issue is None:
            raise KeyError(f"Issue {issue_id} was not found")
        return issue

    def get_issue_by_sequence(self, project_id: int, sequence: int) -> Issue | None:
        return self.session.scalar(
            select(Issue).where(Issue.project_id == project_id, Issue.sequence == sequence)
        )

    def search_issues(
        self, project_id: int | None = None, status: IssueStatus | None = None, limit: int = 20
    ) -> list[Issue]:
        stmt = select(Issue).options(selectinload(Issue.category)).order_by(Issue.sequence).limit(limit)
        if project_id is not None:
            stmt = stmt.where(Issue.project_id == project_id)
        if status is not None:
            stmt = stmt.where(Issue.status == status)
        return list(self.session.scalars(stmt))

    def list_project_issues(self, project_id: int) -> list[Issue]:
        return list(
            self.session.scalars(
                select(Issue)
                .options(selectinload(Issue.category))
                .where(Issue.project_id == project_id)
                .order_by(Issue.sequence)
            )
        )

    def list_issue_events(self, project_id: int, limit: int = 50) -> list[IssueEvent]:
        return list(
            self.session.scalars(
                select(IssueEvent)
                .join(Issue, Issue.id == IssueEvent.issue_id)
                .where(Issue.project_id == project_id)
                .order_by(IssueEvent.created_at.desc(), IssueEvent.id.desc())
                .limit(limit)
            )
        )

    def list_dependencies_for_issue(self, issue_id: int) -> list[IssueDependency]:
        return list(
            self.session.scalars(
                select(IssueDependency).where(
                    (IssueDependency.blocker_issue_id == issue_id)
                    | (IssueDependency.blocked_issue_id == issue_id)
                )
            )
        )

    def dependency_exists(self, blocker_issue_id: int, blocked_issue_id: int) -> bool:
        return (
            self.session.scalar(
                select(IssueDependency.id).where(
                    IssueDependency.blocker_issue_id == blocker_issue_id,
                    IssueDependency.blocked_issue_id == blocked_issue_id,
                )
            )
            is not None
        )

    def children_for_blocker(self, blocker_issue_id: int) -> list[int]:
        return list(
            self.session.scalars(
                select(IssueDependency.blocked_issue_id).where(
                    IssueDependency.blocker_issue_id == blocker_issue_id
                )
            )
        )

    def get_sprint(self, sprint_id: int) -> Sprint:
        sprint = self.session.get(Sprint, sprint_id)
        if sprint is None:
            raise KeyError(f"Sprint {sprint_id} was not found")
        return sprint

    def list_project_sprints(self, project_id: int) -> list[Sprint]:
        return list(
            self.session.scalars(
                select(Sprint).where(Sprint.project_id == project_id).order_by(Sprint.sequence.desc())
            )
        )

    def active_sprint(self, project_id: int) -> Sprint | None:
        return self.session.scalar(
            select(Sprint)
            .where(Sprint.project_id == project_id, Sprint.status != SprintStatus.CLOSED)
            .order_by(Sprint.sequence.desc())
        )

    def list_sprint_issues(self, sprint_id: int) -> list[SprintIssue]:
        return list(
            self.session.scalars(
                select(SprintIssue).where(SprintIssue.sprint_id == sprint_id).order_by(SprintIssue.sort_order)
            )
        )

    def list_issue_logs(self, project_id: int) -> list[IssueLogEntry]:
        return list(
            self.session.scalars(
                select(IssueLogEntry)
                .where(IssueLogEntry.project_id == project_id)
                .order_by(IssueLogEntry.created_at.desc())
            )
        )

    def list_linked_prs(self, issue_id: int | None = None) -> list[LinkedPR]:
        stmt = select(LinkedPR)
        if issue_id is not None:
            stmt = stmt.where(LinkedPR.issue_id == issue_id)
        return list(self.session.scalars(stmt))


def record_event(session: Session, issue_id: int, event_type: str, message: str, actor: str | None = None) -> None:
    session.add(IssueEvent(issue_id=issue_id, event_type=event_type, message=message, actor=actor))
