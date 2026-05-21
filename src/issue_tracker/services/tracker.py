from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from issue_tracker.domain.enums import IssueStatus, SprintStatus
from issue_tracker.domain.models import (
    Category,
    Issue,
    IssueDependency,
    IssueLogEntry,
    Project,
    Sprint,
    SprintIssue,
    User,
)
from issue_tracker.repositories.store import Repository, record_event


class DomainError(ValueError):
    pass


def display_id(sequence: int) -> str:
    return f"{sequence:04d}"


def slugify(sequence: int, text: str) -> str:
    body = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "item"
    return f"{display_id(sequence)}-{body[:120]}"


@dataclass(frozen=True)
class IssueSummary:
    id: int
    sequence: int
    title: str
    status: str
    priority: str

    @property
    def display_id(self) -> str:
        return f"{self.sequence:04d}"


class AuthService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = Repository(session)

    def setup_admin(self, username: str, password_hash: str) -> User:
        if self.repo.count_users() > 0:
            raise DomainError("Admin user is already configured")
        user = User(username=username.strip(), password_hash=password_hash)
        self.repo.add(user)
        self._commit()
        return user

    def get_user(self, username: str) -> User | None:
        return self.repo.get_user_by_username(username.strip())

    def setup_required(self) -> bool:
        return self.repo.count_users() == 0

    def _commit(self) -> None:
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise DomainError("Admin user violates a unique constraint") from exc


class ProjectService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = Repository(session)

    def create_project(
        self,
        name: str,
        repo_url: str | None = None,
        default_branch: str = "main",
        tracker_path_hint: str | None = None,
        rules_path_hint: str | None = None,
    ) -> Project:
        if not name.strip():
            raise DomainError("Project name is required")
        project = Project(
            name=name.strip(),
            repo_url=repo_url or None,
            default_branch=default_branch.strip() or "main",
            tracker_path_hint=tracker_path_hint or None,
            rules_path_hint=rules_path_hint or None,
        )
        self.repo.add(project)
        self._commit()
        return project

    def list_projects(self) -> list[Project]:
        return self.repo.list_projects()

    def get_project(self, project_id: int) -> Project:
        return self.repo.get_project(project_id)

    def _commit(self) -> None:
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise DomainError("Project violates a unique constraint") from exc


class CategoryService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = Repository(session)

    def create_category(
        self,
        project_id: int,
        key: str,
        name: str,
        checklist: str,
        description: str | None = None,
    ) -> Category:
        if not key.strip() or not name.strip() or not checklist.strip():
            raise DomainError("Category key, name, and checklist are required")
        category = Category(
            project_id=project_id,
            key=key.strip(),
            name=name.strip(),
            checklist=checklist.strip(),
            description=description or None,
        )
        self.repo.add(category)
        self._commit("Category violates a unique constraint")
        return category

    def list_categories(self, project_id: int) -> list[Category]:
        return self.repo.list_categories(project_id)

    def _commit(self, message: str) -> None:
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise DomainError(message) from exc


class IssueService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = Repository(session)

    def create_issue(
        self,
        project_id: int,
        title: str,
        acceptance_criteria: str,
        priority: str = "normal",
        summary: str | None = None,
        proposed_approach: str | None = None,
        category_id: int | None = None,
        labels: list[str] | None = None,
    ) -> Issue:
        if not title.strip():
            raise DomainError("Issue title is required")
        if not acceptance_criteria.strip():
            raise DomainError("Acceptance criteria are required")
        category = self.repo.get_category(category_id)
        if category and category.project_id != project_id:
            raise DomainError("Category belongs to another project")
        sequence = self.repo.allocate_sequence(project_id)
        issue = Issue(
            project_id=project_id,
            sequence=sequence,
            slug=slugify(sequence, title),
            title=title.strip(),
            priority=priority.strip() or "normal",
            labels={"items": labels or []},
            summary=summary or None,
            proposed_approach=proposed_approach or None,
            acceptance_criteria=acceptance_criteria.strip(),
            category_id=category_id,
        )
        self.repo.add(issue)
        self.session.flush()
        record_event(self.session, issue.id, "created", f"Issue {display_id(sequence)} created")
        self._commit("Issue violates a database invariant")
        return issue

    def get_issue(self, issue_id: int) -> Issue:
        return self.repo.get_issue(issue_id)

    def get_issue_by_sequence(self, project_id: int, sequence: int) -> Issue:
        issue = self.repo.get_issue_by_sequence(project_id, sequence)
        if issue is None:
            raise DomainError(f"Issue {display_id(sequence)} was not found")
        return issue

    def search(self, project_id: int | None = None, status: str | None = None, limit: int = 20) -> list[Issue]:
        bounded_limit = max(1, min(limit, 50))
        parsed_status = IssueStatus(status) if status else None
        return self.repo.search_issues(project_id=project_id, status=parsed_status, limit=bounded_limit)

    def update_status(
        self,
        issue_id: int,
        status: str,
        originating_llm: str | None = None,
        closed_by: str | None = None,
        close_note: str | None = None,
        actor: str | None = None,
    ) -> Issue:
        issue = self.repo.get_issue(issue_id)
        new_status = IssueStatus(status)
        if issue.status == IssueStatus.DONE and issue.closed_at is not None:
            if new_status != IssueStatus.DONE:
                raise DomainError("Closed issue metadata is immutable")
            return issue
        if new_status == IssueStatus.DONE:
            if not originating_llm:
                raise DomainError("Originating LLM is required to close an issue")
            issue.originating_llm = originating_llm
            issue.closed_by = closed_by or actor
            issue.close_note = close_note or None
            issue.closed_at = datetime.now(UTC)
        issue.status = new_status
        record_event(self.session, issue.id, "status", f"Status changed to {new_status.value}", actor)
        self._commit("Issue status update failed")
        return issue

    def add_dependency(self, blocker_issue_id: int, blocked_issue_id: int) -> IssueDependency:
        if blocker_issue_id == blocked_issue_id:
            raise DomainError("An issue cannot block itself")
        blocker = self.repo.get_issue(blocker_issue_id)
        blocked = self.repo.get_issue(blocked_issue_id)
        if blocker.project_id != blocked.project_id:
            raise DomainError("Dependencies must stay inside one project")
        if self.repo.dependency_exists(blocker_issue_id, blocked_issue_id):
            raise DomainError("Dependency already exists")
        if self._path_exists(start=blocked_issue_id, target=blocker_issue_id):
            raise DomainError("Dependency would create a cycle")
        dependency = IssueDependency(
            project_id=blocker.project_id,
            blocker_issue_id=blocker_issue_id,
            blocked_issue_id=blocked_issue_id,
        )
        self.repo.add(dependency)
        self._commit("Dependency violates a database invariant")
        return dependency

    def _path_exists(self, start: int, target: int) -> bool:
        seen: set[int] = set()
        stack = [start]
        while stack:
            current = stack.pop()
            if current == target:
                return True
            if current in seen:
                continue
            seen.add(current)
            stack.extend(self.repo.children_for_blocker(current))
        return False

    def _commit(self, message: str) -> None:
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise DomainError(message) from exc


class SprintService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = Repository(session)

    def create_sprint(self, project_id: int, goal: str, context: str | None = None) -> Sprint:
        if not goal.strip():
            raise DomainError("Sprint goal is required")
        sequence = self.repo.allocate_sequence(project_id)
        sprint = Sprint(
            project_id=project_id,
            sequence=sequence,
            slug=slugify(sequence, goal),
            goal=goal.strip(),
            context=context or None,
            status=SprintStatus.ACTIVE,
        )
        self.repo.add(sprint)
        self._commit("Sprint violates a database invariant")
        return sprint

    def add_issue(self, sprint_id: int, issue_id: int, phase: str | None = None) -> SprintIssue:
        sprint = self.repo.get_sprint(sprint_id)
        issue = self.repo.get_issue(issue_id)
        if sprint.project_id != issue.project_id:
            raise DomainError("Sprint and issue belong to different projects")
        issue.status = IssueStatus.IN_PROGRESS
        membership = SprintIssue(
            sprint_id=sprint_id,
            issue_id=issue_id,
            phase=phase or None,
            sort_order=len(self.repo.list_sprint_issues(sprint_id)) + 1,
        )
        self.repo.add(membership)
        record_event(self.session, issue.id, "sprint", f"Added to Sprint {display_id(sprint.sequence)}")
        self._commit("Sprint membership violates a database invariant")
        return membership

    def close_sprint(self, sprint_id: int) -> Sprint:
        sprint = self.repo.get_sprint(sprint_id)
        if sprint.status != SprintStatus.CLOSED:
            sprint.status = SprintStatus.CLOSED
            sprint.closed_at = datetime.now(UTC)
            self.session.commit()
        return sprint

    def get_sprint(self, sprint_id: int) -> Sprint:
        return self.repo.get_sprint(sprint_id)

    def next_action(self, project_id: int) -> dict[str, object]:
        active = self.repo.active_sprint(project_id)
        blocked = self.repo.search_issues(project_id=project_id, status=IssueStatus.IN_PROGRESS, limit=10)
        backlog = self.repo.search_issues(project_id=project_id, status=IssueStatus.BACKLOG, limit=1)
        return {
            "project_id": project_id,
            "active_sprint_id": active.id if active else None,
            "next_issue": compact_issue(backlog[0]) if backlog else None,
            "in_progress_count": len(blocked),
        }

    def _commit(self, message: str) -> None:
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise DomainError(message) from exc


class IssueLogService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = Repository(session)

    def create_entry(
        self,
        project_id: int,
        root_cause: str,
        prevention_added: str,
        issue_id: int | None = None,
        category_id: int | None = None,
    ) -> IssueLogEntry:
        if not root_cause.strip() or not prevention_added.strip():
            raise DomainError("Root cause and prevention added are required")
        entry = IssueLogEntry(
            project_id=project_id,
            issue_id=issue_id,
            category_id=category_id,
            root_cause=root_cause.strip(),
            prevention_added=prevention_added.strip(),
        )
        self.repo.add(entry)
        self.session.commit()
        return entry

    def list_entries(self, project_id: int) -> list[IssueLogEntry]:
        return self.repo.list_issue_logs(project_id)


def compact_issue(issue: Issue) -> dict[str, object]:
    return {
        "id": issue.id,
        "sequence": display_id(issue.sequence),
        "title": issue.title,
        "status": issue.status.value,
        "priority": issue.priority,
    }


def detailed_issue(issue: Issue) -> dict[str, object]:
    data = compact_issue(issue)
    data.update(
        {
            "summary": issue.summary,
            "proposed_approach": issue.proposed_approach,
            "acceptance_criteria": issue.acceptance_criteria,
            "originating_llm": issue.originating_llm,
            "closed_at": issue.closed_at.isoformat() if issue.closed_at else None,
        }
    )
    return data
