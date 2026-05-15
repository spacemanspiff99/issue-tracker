from __future__ import annotations

from sqlalchemy.orm import Session

from issue_tracker.repositories.store import Repository
from issue_tracker.services.tracker import (
    CategoryService,
    IssueService,
    ProjectService,
    SprintService,
    compact_issue,
    detailed_issue,
    display_id,
)


def project_list(session: Session) -> dict[str, object]:
    projects = []
    repo = Repository(session)
    for project in ProjectService(session).list_projects():
        active = repo.active_sprint(project.id)
        projects.append({"id": project.id, "name": project.name, "active_sprint_id": active.id if active else None})
    return {"projects": projects}


def issue_create(
    session: Session,
    project_id: int,
    title: str,
    acceptance_criteria: str,
    category_id: int | None = None,
):
    issue = IssueService(session).create_issue(project_id, title, acceptance_criteria, category_id=category_id)
    return {"issue": compact_issue(issue), "next": "Use issue.get with include_full=true for full details."}


def issue_get(session: Session, issue_id: int, include_full: bool = False):
    issue = IssueService(session).get_issue(issue_id)
    return {"issue": detailed_issue(issue) if include_full else compact_issue(issue)}


def issue_search(session: Session, project_id: int | None = None, status: str | None = None, limit: int = 20):
    issues = IssueService(session).search(project_id=project_id, status=status, limit=limit)
    return {"issues": [compact_issue(issue) for issue in issues], "limit": min(max(limit, 1), 50)}


def issue_update_status(
    session: Session,
    issue_id: int,
    status: str,
    originating_llm: str | None = None,
    closed_by: str | None = None,
    close_note: str | None = None,
):
    issue = IssueService(session).update_status(
        issue_id,
        status,
        originating_llm=originating_llm,
        closed_by=closed_by,
        close_note=close_note,
        actor=closed_by,
    )
    return {"issue": compact_issue(issue), "closed_at": issue.closed_at.isoformat() if issue.closed_at else None}


def issue_add_dependency(session: Session, blocker_issue_id: int, blocked_issue_id: int):
    dependency = IssueService(session).add_dependency(blocker_issue_id, blocked_issue_id)
    return {
        "dependency": {
            "id": dependency.id,
            "blocker_issue_id": dependency.blocker_issue_id,
            "blocked_issue_id": dependency.blocked_issue_id,
        }
    }


def sprint_create(session: Session, project_id: int, goal: str, context: str | None = None):
    sprint = SprintService(session).create_sprint(project_id, goal, context)
    return {
        "sprint": {
            "id": sprint.id,
            "sequence": display_id(sprint.sequence),
            "goal": sprint.goal,
            "status": sprint.status.value,
        }
    }


def sprint_add_issue(session: Session, sprint_id: int, issue_id: int):
    membership = SprintService(session).add_issue(sprint_id, issue_id)
    return {
        "sprint_issue": {
            "id": membership.id,
            "sprint_id": sprint_id,
            "issue_id": issue_id,
            "status": membership.status.value,
        }
    }


def sprint_get(session: Session, sprint_id: int):
    sprint = SprintService(session).get_sprint(sprint_id)
    memberships = Repository(session).list_sprint_issues(sprint_id)
    return {
        "sprint": {
            "id": sprint.id,
            "sequence": display_id(sprint.sequence),
            "goal": sprint.goal,
            "status": sprint.status.value,
        },
        "issues": [compact_issue(m.issue) for m in memberships],
    }


def category_list(session: Session, project_id: int):
    categories = CategoryService(session).list_categories(project_id)
    return {"categories": [{"id": c.id, "key": c.key, "name": c.name} for c in categories]}


def next_action(session: Session, project_id: int):
    return SprintService(session).next_action(project_id)
