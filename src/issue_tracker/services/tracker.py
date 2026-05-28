from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

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
from issue_tracker.repositories.store import Repository, record_event


class DomainError(ValueError):
    pass


ISSUE_STATUS_ORDER = ["backlog", "in-progress", "done", "cancelled"]
ISSUE_STATUS_LABELS = {
    "backlog": "Backlog",
    "in-progress": "In Progress",
    "done": "Done",
    "cancelled": "Cancelled / Won't Do",
}
WORKFLOW_STATE_ORDER = [
    "needs-processing",
    "needs-clarification",
    "ready-for-codex",
    "implementing",
    "verifying",
    "closed",
]
WORKFLOW_STATE_LABELS = {
    "needs-processing": "Needs processing",
    "needs-clarification": "Needs clarification",
    "ready-for-codex": "Ready for Codex",
    "implementing": "Implementing",
    "verifying": "Verifying",
    "closed": "Closed",
}
WORKFLOW_STATE_ALIASES = {
    "intake": "needs-processing",
    "needs processing": "needs-processing",
    "needs-processing": "needs-processing",
    "clarify": "needs-clarification",
    "needs clarification": "needs-clarification",
    "needs-clarification": "needs-clarification",
    "ready for codex": "ready-for-codex",
    "ready-for-codex": "ready-for-codex",
    "implementing": "implementing",
    "verifying": "verifying",
    "closed": "closed",
}
BACKLOG_SAVED_VIEWS = [
    "all",
    "needs-processing",
    "needs-clarification",
    "ready-for-codex",
    "unsprinted-ready",
    "blocked",
    "done",
    "cancelled",
    "backlog",
    "active-sprint",
    "uncategorized",
    "not-in-sprint",
]


def display_id(sequence: int) -> str:
    return f"{sequence:04d}"


def slugify(sequence: int, text: str) -> str:
    body = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "item"
    return f"{display_id(sequence)}-{body[:120]}"


def normalize_workflow_state(value: str) -> str:
    state = WORKFLOW_STATE_ALIASES.get(value.strip().lower())
    if state is None:
        raise DomainError("Workflow state is not supported")
    return state


def issue_workflow_state(issue: Issue) -> str:
    custom_fields = (issue.labels or {}).get("custom_fields")
    state = custom_fields.get("workflow_state") if isinstance(custom_fields, dict) else None
    if isinstance(state, str) and state:
        return normalize_workflow_state(state)
    if issue.status in {IssueStatus.DONE, IssueStatus.CANCELLED}:
        return "closed"
    if issue.status == IssueStatus.IN_PROGRESS:
        return "implementing"
    return "ready-for-codex" if issue.acceptance_criteria.strip() else "needs-processing"


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

    def list_projects(self, include_inactive: bool = False) -> list[Project]:
        projects = self.repo.list_projects()
        if include_inactive:
            return projects
        return [project for project in projects if project.active]

    def search_projects(self, query: str, include_inactive: bool = False) -> list[Project]:
        if not query.strip():
            return self.list_projects(include_inactive=include_inactive)
        projects = self.repo.search_projects(query)
        if include_inactive:
            return projects
        return [project for project in projects if project.active]

    def get_project(self, project_id: int) -> Project:
        return self.repo.get_project(project_id)

    def set_project_active(self, project_id: int, active: bool) -> Project:
        project = self.repo.get_project(project_id)
        project.active = active
        self._commit()
        return project

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
        return sorted(
            self.repo.list_categories(project_id),
            key=lambda category: (category.name.lower(), category.key.lower()),
        )

    def ensure_base_taxonomy(self, project_id: int) -> list[Category]:
        existing = {category.key for category in self.repo.list_categories(project_id)}
        base = [
            ("BUG", "Bug", "Capture the user-visible failure, reproduction path, expected behavior, and verification."),
            ("DOCS", "Docs", "Update durable guidance, prompts, planning notes, or evidence links."),
            ("FEATURE", "Feature", "Define the user workflow, acceptance criteria, and verification path."),
            ("OPS", "Operations", "Verify runtime, deployment, backup, configuration, or observability behavior."),
            (
                "UX",
                "User Experience",
                "Check navigation, copy, accessibility, responsive layout, and workflow clarity.",
            ),
            ("IT-1", "Tracker State Integrity", "Verify tracker state before and after mutations."),
            ("IT-2", "Category And AC Binding", "Keep category selection and acceptance criteria explicit."),
            ("IT-3", "Schema And Migration Safety", "Run migration gates for schema changes."),
            ("IT-4", "MCP Contract And Token Discipline", "Keep MCP responses compact and service-backed."),
            ("IT-5", "Auth And Secret Safety", "Avoid leaking credentials and preserve session controls."),
            ("IT-6", "Deployment And Configuration Drift", "Verify Docker and health checks after config changes."),
        ]
        created: list[Category] = []
        for key, name, checklist in base:
            if key not in existing:
                created.append(
                    Category(project_id=project_id, key=key, name=name, checklist=checklist)
                )
        for category in created:
            self.repo.add(category)
        if created:
            self._commit("Base taxonomy violates a unique constraint")
        return self.list_categories(project_id)

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
        if category_id is not None and category is None:
            raise DomainError("Category was not found")
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

    def saved_views(self) -> list[dict[str, str]]:
        labels = {
            "all": "All",
            "needs-processing": "Needs processing",
            "needs-clarification": "Needs clarification",
            "ready-for-codex": "Ready for Codex",
            "unsprinted-ready": "Unsprinted ready work",
            "blocked": "Blocked",
            "done": "Done",
            "cancelled": "Cancelled / Won't Do",
            "backlog": "Backlog",
            "active-sprint": "Active Sprint",
            "uncategorized": "Uncategorized",
            "not-in-sprint": "Issues Not In Sprint",
        }
        descriptions = {
            "all": "Every issue in the project.",
            "needs-processing": "Raw intake that needs a human or Codex processing pass.",
            "needs-clarification": "Work blocked on exact owner questions before implementation.",
            "ready-for-codex": "Build-ready work with executable acceptance criteria.",
            "unsprinted-ready": "Ready-for-Codex work with no sprint membership.",
            "blocked": "Issues with open blocker dependencies.",
            "done": "Completed issues with close metadata.",
            "cancelled": "Closed historical work that was cancelled or marked won't do.",
            "backlog": "Open issues not currently in progress.",
            "active-sprint": "Issues assigned to the active or current sprint.",
            "uncategorized": "Issues still missing project-scoped category binding.",
            "not-in-sprint": "Open issues with no sprint membership.",
        }
        return [{"key": key, "label": labels[key], "description": descriptions[key]} for key in BACKLOG_SAVED_VIEWS]

    def status_options(self) -> list[dict[str, str]]:
        return [{"value": status, "label": ISSUE_STATUS_LABELS[status]} for status in ISSUE_STATUS_ORDER]

    def workflow_options(self) -> list[dict[str, str]]:
        return [{"value": state, "label": WORKFLOW_STATE_LABELS[state]} for state in WORKFLOW_STATE_ORDER]

    def list_project_view(
        self,
        project_id: int,
        view: str = "all",
        query: str = "",
        status: str | None = None,
        workflow_state: str | None = None,
        milestone: str = "",
        category_id: int | None = None,
        unscheduled: bool = False,
    ) -> list[Issue]:
        issues = self.repo.list_project_issues(project_id)
        if query.strip():
            needle = query.strip().lower()
            issues = [
                issue
                for issue in issues
                if needle in issue.title.lower()
                or needle in (issue.summary or "").lower()
                or needle in issue.acceptance_criteria.lower()
                or needle in (issue.category.key.lower() if issue.category else "")
                or needle in " ".join(str(item).lower() for item in (issue.labels or {}).get("items", []))
            ]
        active = self.repo.current_sprint(project_id)
        active_issue_ids = {m.issue_id for m in self.repo.list_sprint_issues(active.id)} if active else set()
        sprint_issue_ids = {
            membership.issue_id
            for sprint in self.repo.list_project_sprints(project_id)
            for membership in self.repo.list_sprint_issues(sprint.id)
        }
        if view == "backlog":
            issues = [issue for issue in issues if issue.status == IssueStatus.BACKLOG]
        elif view == "active-sprint":
            issues = [issue for issue in issues if issue.id in active_issue_ids]
        elif view == "blocked":
            issues = [issue for issue in issues if self.blocked_by_open_dependencies(issue.id)]
        elif view == "done":
            issues = [issue for issue in issues if issue.status == IssueStatus.DONE]
        elif view == "cancelled":
            issues = [issue for issue in issues if issue.status == IssueStatus.CANCELLED]
        elif view == "uncategorized":
            issues = [issue for issue in issues if issue.category_id is None]
        elif view == "not-in-sprint":
            issues = [issue for issue in issues if issue.id not in sprint_issue_ids and not self._terminal(issue)]
        elif view in WORKFLOW_STATE_ORDER:
            issues = [issue for issue in issues if self.workflow_state(issue) == view]
        elif view == "unsprinted-ready":
            issues = [
                issue
                for issue in issues
                if issue.id not in sprint_issue_ids
                and not self._terminal(issue)
                and self.workflow_state(issue) == "ready-for-codex"
            ]
        if status:
            parsed_status = IssueStatus(status)
            issues = [issue for issue in issues if issue.status == parsed_status]
        if workflow_state:
            parsed_workflow_state = normalize_workflow_state(workflow_state)
            issues = [issue for issue in issues if self.workflow_state(issue) == parsed_workflow_state]
        if milestone:
            issues = [issue for issue in issues if str(self._meta(issue).get("milestone") or "Unplanned") == milestone]
        if category_id is not None:
            issues = [issue for issue in issues if issue.category_id == category_id]
        if unscheduled:
            issues = [issue for issue in issues if issue.id not in sprint_issue_ids]
        return sorted(issues, key=lambda issue: (self._rank(issue), issue.sequence))

    def project_summary(self, project_id: int) -> dict[str, object]:
        issues = self.repo.list_project_issues(project_id)
        by_status = {status.value: 0 for status in IssueStatus}
        blocked = 0
        uncategorized = 0
        for issue in issues:
            by_status[issue.status.value] += 1
            if self.blocked_by_open_dependencies(issue.id):
                blocked += 1
            if issue.category_id is None:
                uncategorized += 1
        done = by_status[IssueStatus.DONE.value]
        total = len(issues)
        deliverable_total = sum(1 for issue in issues if issue.status != IssueStatus.CANCELLED)
        return {
            "total": total,
            "by_status": by_status,
            "blocked": blocked,
            "uncategorized": uncategorized,
            "done_percent": round((done / deliverable_total) * 100) if deliverable_total else 0,
        }

    def overview_dashboard(self, project_id: int) -> dict[str, object]:
        issues = self.repo.list_project_issues(project_id)
        delivery_phases: dict[str, int] = {}
        blocked_items = []
        workflow_counts = self.workflow_summary(project_id)
        for issue in issues:
            meta = self._meta(issue)
            phase = str(meta.get("delivery_phase") or "Unassigned")
            delivery_phases[phase] = delivery_phases.get(phase, 0) + 1
            health = self.dependency_health(issue.id)
            if health["blocked"]:
                blocked_items.append(
                    {
                        "issue": issue,
                        "blockers": health["open_blockers"],
                        "reason": ", ".join(
                            f"{display_id(blocker.sequence)} {blocker.title}" for blocker in health["open_blockers"]
                        ),
                    }
                )
        active = self.repo.current_sprint(project_id)
        active_memberships = self.repo.list_sprint_issues(active.id) if active else []
        active_by_status = {status.value: 0 for status in IssueStatus}
        for membership in active_memberships:
            active_by_status[membership.issue.status.value] += 1
        return {
            "status_counts": self.project_summary(project_id)["by_status"],
            "status_labels": ISSUE_STATUS_LABELS,
            "workflow_counts": workflow_counts,
            "workflow_labels": WORKFLOW_STATE_LABELS,
            "delivery_phases": delivery_phases,
            "blocked_items": blocked_items,
            "active_sprint": active,
            "active_sprint_total": len(active_memberships),
            "active_sprint_by_status": active_by_status,
        }

    def sprint_rollups(self, project_id: int) -> list[dict[str, object]]:
        rollups = []
        for sprint in self.repo.list_project_sprints(project_id):
            memberships = self.repo.list_sprint_issues(sprint.id)
            total = len(memberships)
            done = sum(1 for membership in memberships if membership.issue.status == IssueStatus.DONE)
            blocked = sum(1 for membership in memberships if self.blocked_by_open_dependencies(membership.issue_id))
            stories: dict[str, int] = {}
            for membership in memberships:
                story = self._meta(membership.issue).get("story") or "Unassigned"
                stories[str(story)] = stories.get(str(story), 0) + 1
            rollups.append(
                {
                    "sprint": sprint,
                    "total": total,
                    "done": done,
                    "blocked": blocked,
                    "done_percent": round((done / total) * 100) if total else 0,
                    "stories": stories,
                }
            )
        return sorted(rollups, key=lambda item: item["sprint"].sequence, reverse=True)

    def sprint_navigation(self, project_id: int) -> dict[str, list[Sprint]]:
        sprints = self.repo.list_project_sprints(project_id)
        return {
            "current": [sprint for sprint in sprints if sprint.status == SprintStatus.ACTIVE],
            "planned": [sprint for sprint in sprints if sprint.status == SprintStatus.PLANNED],
            "history": [sprint for sprint in sprints if sprint.status == SprintStatus.CLOSED],
        }

    def release_rollups(self, project_id: int) -> list[dict[str, object]]:
        issues = self.repo.list_project_issues(project_id)
        sprints = self.repo.list_project_sprints(project_id)
        sprint_issue_ids = {
            membership.issue_id
            for sprint in sprints
            for membership in self.repo.list_sprint_issues(sprint.id)
        }
        releases: dict[str, dict[str, object]] = {}
        for issue in issues:
            milestone = str(self._meta(issue).get("milestone") or "Unplanned")
            release = releases.setdefault(
                milestone,
                {
                    "name": milestone,
                    "total": 0,
                    "done": 0,
                    "blocked": 0,
                    "unscheduled": 0,
                    "issues": [],
                    "sprints": set(),
                    "readiness_notes": [],
                },
            )
            release["total"] = int(release["total"]) + 1
            if issue.status == IssueStatus.DONE:
                release["done"] = int(release["done"]) + 1
            if self.blocked_by_open_dependencies(issue.id):
                release["blocked"] = int(release["blocked"]) + 1
            if issue.id not in sprint_issue_ids:
                release["unscheduled"] = int(release["unscheduled"]) + 1
            release["issues"].append(issue)  # type: ignore[union-attr]
            custom_fields = self._meta(issue).get("custom_fields")
            if isinstance(custom_fields, dict) and custom_fields.get("readiness"):
                release["readiness_notes"].append(str(custom_fields["readiness"]))  # type: ignore[union-attr]
        for sprint in sprints:
            for membership in self.repo.list_sprint_issues(sprint.id):
                milestone = str(self._meta(membership.issue).get("milestone") or "Unplanned")
                if milestone in releases:
                    releases[milestone]["sprints"].add(sprint)  # type: ignore[union-attr]
        ordered = sorted(
            releases.values(),
            key=lambda item: (str(item["name"]) == "Unplanned", str(item["name"]).lower()),
        )
        for release in ordered:
            total = int(release["total"])
            release["done_percent"] = round((int(release["done"]) / total) * 100) if total else 0
            release["sprints"] = sorted(release["sprints"], key=lambda sprint: sprint.sequence)  # type: ignore[arg-type]
            release["section"] = self._release_section(release)
        return ordered

    def release_sections(self, project_id: int) -> dict[str, list[dict[str, object]]]:
        sections: dict[str, list[dict[str, object]]] = {
            "current": [],
            "upcoming": [],
            "archive": [],
            "unplanned": [],
        }
        for release in self.release_rollups(project_id):
            sections[str(release["section"])].append(release)
        return sections

    def workflow_summary(self, project_id: int) -> dict[str, int]:
        states = {state: 0 for state in WORKFLOW_STATE_ORDER}
        for issue in self.repo.list_project_issues(project_id):
            state = self.workflow_state(issue)
            states[state] = states.get(state, 0) + 1
        return states

    def workflow_state(self, issue: Issue) -> str:
        return issue_workflow_state(issue)

    def update_workflow_state(self, issue_id: int, workflow_state: str, actor: str | None = None) -> Issue:
        normalized_state = normalize_workflow_state(workflow_state)
        issue = self.repo.get_issue(issue_id)
        meta = self._meta(issue)
        custom_fields = dict(meta.get("custom_fields") or {})
        custom_fields["workflow_state"] = normalized_state
        meta["custom_fields"] = custom_fields
        issue.labels = meta
        record_event(
            self.session,
            issue.id,
            "workflow",
            f"Workflow state changed to {WORKFLOW_STATE_LABELS[normalized_state]}",
            actor,
        )
        self._commit("Workflow state update failed")
        return issue

    def create_voice_intake(
        self,
        project_id: int,
        title: str,
        notes: str,
        stored_audio_path: Path | None,
        ambiguous: bool,
        priority: str = "normal",
        actor: str | None = None,
    ) -> Issue:
        clean_priority = priority.strip() or "normal"
        audio_only = stored_audio_path is not None and not title.strip() and not notes.strip()
        if audio_only and clean_priority == "urgent":
            clean_title = "To process: urgent audio note"
        elif audio_only:
            clean_title = "To process: audio note"
        else:
            clean_title = title.strip() or "Voice feedback intake"
        state = "needs-clarification" if ambiguous else "needs-processing"
        audio_note = f"\n- Audio artifact: `{stored_audio_path}`" if stored_audio_path else "\n- Audio artifact: none"
        default_summary = (
            "Audio-only urgent voice note awaiting Codex processing."
            if audio_only and clean_priority == "urgent"
            else "Audio-only voice feedback intake."
        )
        acceptance_criteria = (
            "- [ ] Codex reviews the submitted voice feedback and written notes.\n"
            "- [ ] The intake is converted into Ready for Codex work or marked Needs clarification.\n"
            "- [ ] Raw audio remains in ignored local artifacts and is not committed."
        )
        labels = ["voice-feedback", "intake"]
        if clean_priority == "urgent":
            labels.append(clean_priority)
        issue = self.create_issue(
            project_id,
            f"Voice feedback: {clean_title}",
            acceptance_criteria,
            priority=clean_priority,
            summary=(notes.strip() or default_summary) + audio_note,
            proposed_approach="Process this intake through Codex investigation before implementation.",
            labels=labels,
        )
        meta = self._meta(issue)
        custom_fields = dict(meta.get("custom_fields") or {})
        custom_fields.update(
            {
                "workflow_state": state,
                "intake_type": "voice-feedback",
                "audio_path": str(stored_audio_path) if stored_audio_path else "",
            }
        )
        meta["custom_fields"] = custom_fields
        issue.labels = meta
        record_event(self.session, issue.id, "voice-intake", "Voice feedback intake created", actor)
        self._commit("Voice intake failed")
        return issue

    def delete_voice_intake(self, issue_id: int, actor: str | None = None) -> None:
        issue = self.repo.get_issue(issue_id)
        meta = self._meta(issue)
        custom_fields = meta.get("custom_fields") or {}
        if custom_fields.get("intake_type") != "voice-feedback":
            raise DomainError("Only voice feedback intake issues can be deleted from the intake recorder")
        if not self._discard_allowed(issue):
            raise DomainError("Durable work cannot be deleted; cancel or archive it instead")
        audio_path = custom_fields.get("audio_path") or ""
        if audio_path:
            Path(audio_path).unlink(missing_ok=True)
        self.session.delete(issue)
        self._commit("Voice intake delete failed")

    def blocked_by_open_dependencies(self, issue_id: int) -> bool:
        for dependency in self.repo.list_dependencies_for_issue(issue_id):
            if dependency.blocked_issue_id == issue_id and not self._terminal(dependency.blocker):
                return True
        return False

    def dependency_health(self, issue_id: int) -> dict[str, object]:
        dependencies = self.repo.list_dependencies_for_issue(issue_id)
        open_blockers = [
            dependency.blocker
            for dependency in dependencies
            if dependency.blocked_issue_id == issue_id and not self._terminal(dependency.blocker)
        ]
        blocking = [
            dependency.blocked
            for dependency in dependencies
            if dependency.blocker_issue_id == issue_id and not self._terminal(dependency.blocked)
        ]
        return {
            "blocked": bool(open_blockers),
            "open_blockers": open_blockers,
            "blocking": blocking,
        }

    def update_issue(
        self,
        issue_id: int,
        title: str | None = None,
        acceptance_criteria: str | None = None,
        priority: str | None = None,
        summary: str | None = None,
        proposed_approach: str | None = None,
        category_id: int | None = None,
        status: str | None = None,
        actor: str | None = None,
    ) -> Issue:
        issue = self.repo.get_issue(issue_id)
        if title is not None:
            if not title.strip():
                raise DomainError("Issue title is required")
            issue.title = title.strip()
        if acceptance_criteria is not None:
            if not acceptance_criteria.strip():
                raise DomainError("Acceptance criteria are required")
            issue.acceptance_criteria = acceptance_criteria.strip()
        if priority is not None:
            issue.priority = priority.strip() or "normal"
        if summary is not None:
            issue.summary = summary.strip() or None
        if proposed_approach is not None:
            issue.proposed_approach = proposed_approach.strip() or None
        if category_id is not None:
            category = self.repo.get_category(category_id)
            if category is None:
                raise DomainError("Category was not found")
            if category.project_id != issue.project_id:
                raise DomainError("Category belongs to another project")
            issue.category_id = category_id
        if status is not None and IssueStatus(status) != issue.status:
            new_status = IssueStatus(status)
            if self._terminal_status(new_status):
                issue.originating_llm = issue.originating_llm or "gpt-5.5"
                issue.closed_by = issue.closed_by or actor or "web"
                issue.close_note = issue.close_note or (
                    "Cancelled or marked won't do from web status control."
                    if new_status == IssueStatus.CANCELLED
                    else "Closed from web status control."
                )
                issue.closed_at = issue.closed_at or datetime.now(UTC)
            elif self._terminal(issue) and issue.closed_at is not None:
                raise DomainError("Closed issue metadata is immutable")
            issue.status = new_status
            record_event(self.session, issue.id, "status", f"Status changed to {new_status.value}", actor)
        record_event(self.session, issue.id, "updated", "Issue fields updated", actor)
        self._commit("Issue update failed")
        return issue

    def update_planning_metadata(
        self,
        issue_id: int,
        labels: str = "",
        story: str = "",
        delivery_phase: str = "",
        milestone: str = "",
        custom_fields: str = "",
        actor: str | None = None,
    ) -> Issue:
        issue = self.repo.get_issue(issue_id)
        meta = self._meta(issue)
        meta["items"] = [item.strip() for item in labels.split(",") if item.strip()]
        meta["story"] = story.strip()
        meta["delivery_phase"] = delivery_phase.strip()
        meta["milestone"] = milestone.strip()
        meta["custom_fields"] = self._parse_custom_fields(custom_fields)
        issue.labels = meta
        record_event(self.session, issue.id, "metadata", "Planning metadata updated", actor)
        self._commit("Issue metadata update failed")
        return issue

    def add_comment(self, issue_id: int, message: str, actor: str | None = None) -> IssueEvent:
        if not message.strip():
            raise DomainError("Comment is required")
        issue = self.repo.get_issue(issue_id)
        event = IssueEvent(issue_id=issue.id, event_type="comment", message=message.strip(), actor=actor)
        self.repo.add(event)
        self._commit("Issue comment failed")
        return event

    def add_linked_reference(
        self,
        issue_id: int,
        repo: str,
        url: str,
        pr_number: int | None = None,
        merge_status: str | None = None,
        actor: str | None = None,
    ) -> LinkedPR:
        if not repo.strip() or not url.strip():
            raise DomainError("Repository and URL are required")
        issue = self.repo.get_issue(issue_id)
        linked = LinkedPR(
            issue_id=issue.id,
            provider="github",
            repo=repo.strip(),
            pr_number=pr_number,
            url=url.strip(),
            merge_status=merge_status.strip() if merge_status else None,
        )
        self.repo.add(linked)
        record_event(self.session, issue.id, "github", f"Linked GitHub reference {url.strip()}", actor)
        self._commit("Linked reference failed")
        return linked

    def reorder_backlog(self, project_id: int, ordered_issue_ids: list[int]) -> None:
        ranks = {issue_id: index + 1 for index, issue_id in enumerate(ordered_issue_ids)}
        for issue in self.repo.list_project_issues(project_id):
            if issue.id in ranks:
                meta = self._meta(issue)
                meta["rank"] = ranks[issue.id]
                issue.labels = meta
        self._commit("Backlog reorder failed")

    def category_recommendation(self, project_id: int, title: str, acceptance_criteria: str = "") -> Category | None:
        text = f"{title} {acceptance_criteria}".lower()
        categories = self.repo.list_categories(project_id)
        for category in categories:
            haystack = f"{category.key} {category.name} {category.description or ''} {category.checklist}".lower()
            if any(token and token in haystack for token in re.findall(r"[a-z0-9]+", text)):
                return category
        return categories[0] if categories else None

    def activity_feed(self, project_id: int, limit: int = 50) -> list[IssueEvent]:
        return self.repo.list_issue_events(project_id, limit=limit)

    def _rank(self, issue: Issue) -> int:
        value = self._meta(issue).get("rank")
        return int(value) if isinstance(value, int) else 9999

    def _meta(self, issue: Issue) -> dict[str, object]:
        return dict(issue.labels or {})

    def _parse_custom_fields(self, value: str) -> dict[str, str]:
        fields: dict[str, str] = {}
        for line in value.splitlines():
            key, sep, item_value = line.partition("=")
            if sep and key.strip():
                fields[key.strip()] = item_value.strip()
        return fields

    def _terminal_status(self, status: IssueStatus) -> bool:
        return status in {IssueStatus.DONE, IssueStatus.CANCELLED}

    def _terminal(self, issue: Issue) -> bool:
        return self._terminal_status(issue.status)

    def _discard_allowed(self, issue: Issue) -> bool:
        if issue.status != IssueStatus.BACKLOG or issue.closed_at is not None:
            return False
        if self.workflow_state(issue) not in {"needs-processing", "needs-clarification"}:
            return False
        if self.repo.list_dependencies_for_issue(issue.id):
            return False
        if self.repo.list_linked_prs(issue.id):
            return False
        for sprint in self.repo.list_project_sprints(issue.project_id):
            if any(membership.issue_id == issue.id for membership in self.repo.list_sprint_issues(sprint.id)):
                return False
        return True

    def _release_section(self, release: dict[str, object]) -> str:
        if str(release["name"]) == "Unplanned":
            return "unplanned"
        total = int(release["total"])
        done = int(release["done"])
        blocked = int(release["blocked"])
        if total and done == total:
            return "archive"
        if blocked or int(release["unscheduled"]):
            return "current"
        return "upcoming"

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
        if self._terminal(issue) and issue.closed_at is not None:
            if new_status != issue.status:
                raise DomainError("Closed issue metadata is immutable")
            return issue
        if self._terminal_status(new_status):
            if not originating_llm:
                raise DomainError("Originating LLM is required to close an issue")
            if not (closed_by or actor):
                raise DomainError("Closed by is required to close an issue")
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
        if sprint.status == SprintStatus.CLOSED:
            raise DomainError("Closed sprints cannot be changed")
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

    def create_agent_failure(
        self,
        project_id: int,
        target: str,
        observed_failure: str,
        prevention_added: str,
        issue_id: int | None = None,
        category_id: int | None = None,
        severity: str = "medium",
        source_context: str = "",
    ) -> IssueLogEntry:
        root_cause = (
            f"agent-failure | severity={severity.strip() or 'medium'} | target={target.strip()} | "
            f"observed={observed_failure.strip()}"
        )
        if source_context.strip():
            root_cause = f"{root_cause} | source={source_context.strip()}"
        return self.create_entry(project_id, root_cause, prevention_added, issue_id=issue_id, category_id=category_id)

    def create_bug_record(
        self,
        project_id: int,
        bug: str,
        root_cause: str,
        prevention_added: str,
        issue_id: int | None = None,
        category_id: int | None = None,
        severity: str = "medium",
        source_context: str = "",
    ) -> IssueLogEntry:
        cause = f"bug | severity={severity.strip() or 'medium'} | bug={bug.strip()} | root_cause={root_cause.strip()}"
        if source_context.strip():
            cause = f"{cause} | source={source_context.strip()}"
        return self.create_entry(project_id, cause, prevention_added, issue_id=issue_id, category_id=category_id)

    def pattern_summary(self, project_id: int) -> dict[str, int]:
        summary: dict[str, int] = {}
        for entry in self.list_entries(project_id):
            pattern = entry.root_cause.split("|", 1)[0].strip() or "unclassified"
            summary[pattern] = summary.get(pattern, 0) + 1
        return summary


def compact_issue(issue: Issue) -> dict[str, object]:
    return {
        "id": issue.id,
        "sequence": display_id(issue.sequence),
        "title": issue.title,
        "status": issue.status.value,
        "workflow_state": issue_workflow_state(issue),
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
            "closed_by": issue.closed_by,
            "close_note": issue.close_note,
            "closed_at": issue.closed_at.isoformat() if issue.closed_at else None,
        }
    )
    return data
