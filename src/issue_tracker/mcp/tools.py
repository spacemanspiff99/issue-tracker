from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from issue_tracker.repositories.store import Repository
from issue_tracker.services.backup_targets import ArtifactBackupAdapter, VibecodingBackupService
from issue_tracker.services.guidance_sync import GuidanceSyncService
from issue_tracker.services.recovery_bundle import RecoveryBundleService
from issue_tracker.services.rule_relevance import RuleRelevanceService
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


def issue_search(
    session: Session,
    project_id: int | None = None,
    status: str | None = None,
    limit: int = 20,
    view: str = "all",
    query: str = "",
):
    if project_id is not None and (view != "all" or query.strip()):
        issues = IssueService(session).list_project_view(project_id=project_id, view=view, query=query)[:limit]
    else:
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
    return {
        "issue": compact_issue(issue),
        "closed_at": issue.closed_at.isoformat() if issue.closed_at else None,
        "next": "Use issue.get with include_full=true to verify close metadata.",
    }


def issue_add_dependency(session: Session, blocker_issue_id: int, blocked_issue_id: int):
    dependency = IssueService(session).add_dependency(blocker_issue_id, blocked_issue_id)
    return {
        "dependency": {
            "id": dependency.id,
            "blocker_issue_id": dependency.blocker_issue_id,
            "blocked_issue_id": dependency.blocked_issue_id,
            "status": "created",
        },
        "next": "Use issue.get on the blocked issue to review dependency context.",
    }


def sprint_create(session: Session, project_id: int, goal: str, context: str | None = None):
    sprint = SprintService(session).create_sprint(project_id, goal, context)
    return {
        "sprint": {
            "id": sprint.id,
            "sequence": display_id(sprint.sequence),
            "goal": sprint.goal,
            "status": sprint.status.value,
        },
        "next": "Use sprint.add_issue to assign backlog issues.",
    }


def sprint_add_issue(session: Session, sprint_id: int, issue_id: int):
    membership = SprintService(session).add_issue(sprint_id, issue_id)
    return {
        "sprint_issue": {
            "id": membership.id,
            "sprint_id": sprint_id,
            "issue_id": issue_id,
            "status": membership.status.value,
        },
        "next": "Use sprint.get to review assigned issues.",
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


def guidance_sync_health(session: Session, project_id: int):
    dashboard = GuidanceSyncService(session).dashboard(project_id)
    return {
        "project_id": project_id,
        "sources": len(dashboard["sources"]),
        "open_drift": dashboard["drift_count"],
        "scan_status": dashboard["scan_status"],
        "proposals": len(dashboard["proposals"]),
        "next": "Use guidance_sync.drift_list for compact drift details.",
    }


def guidance_sync_drift_list(session: Session, project_id: int, limit: int = 20):
    dashboard = GuidanceSyncService(session).dashboard(project_id)
    bounded = min(max(limit, 1), 50)
    return {
        "drifts": [
            {
                "id": drift.id,
                "path": drift.path,
                "type": drift.drift_type,
                "severity": drift.severity,
                "recommended_action": drift.recommended_action,
            }
            for drift in dashboard["drifts"][:bounded]
        ],
        "limit": bounded,
    }


def guidance_sync_create_proposal(
    session: Session,
    project_id: int,
    drift_id: int,
    action: str,
    issue_id: int,
    owner: str,
    verification_command: str,
):
    proposal = GuidanceSyncService(session).create_proposal(
        project_id,
        drift_id,
        action,
        issue_id,
        owner,
        verification_command,
    )
    return {
        "proposal": {
            "id": proposal.id,
            "status": proposal.status,
            "action": proposal.action,
            "issue_id": proposal.issue_id,
        },
        "next": "Review and approve before execution.",
    }


def backup_health(session: Session, project_id: int):
    health = RecoveryBundleService(session).backup_health(project_id)
    return {
        "project_id": project_id,
        "status": health["status"],
        "bundle": health["bundle"],
        "counts": health["counts"],
        "errors": health["errors"][:5],
        "next": health["next"],
    }


def backup_vibecoding_plan(session: Session, project_id: int):
    paths = VibecodingBackupService(session).plan_target_paths(project_id)
    return {
        "project_id": project_id,
        "latest": paths["latest"],
        "snapshot": paths["snapshot"],
        "next": "Publish only a validated sanitized recovery bundle; raw artifacts stay in encrypted backup storage.",
    }


def backup_artifact_check(session: Session, artifact_names: list[str], backend: str = "restic"):
    result = ArtifactBackupAdapter().prepare_backup(
        artifact_paths=[Path(name) for name in artifact_names],
        backend=backend,
    )
    return {
        "status": result.status,
        "backend": result.backend,
        "archive_id": result.archive_id,
        "blocked_reason": result.blocked_reason,
        "artifacts": result.manifest["artifacts"][:20],
        "next": result.next_action,
    }


def rule_resolve(
    session: Session,
    project_types: list[str],
    changed_paths: list[str] | None = None,
    risk_labels: list[str] | None = None,
    include_full: bool = False,
):
    resolution = RuleRelevanceService().resolve(project_types, changed_paths=changed_paths, risk_labels=risk_labels)
    rules = [
        {
            "rule_id": item.metadata.rule_id,
            "title": item.metadata.title,
            "status": item.status,
            "critical": item.metadata.critical,
            **({"source_path": item.metadata.source_path, "version": item.metadata.version} if include_full else {}),
        }
        for item in resolution.rules[:50]
    ]
    return {
        "status": resolution.status,
        "rules": rules,
        "missing_critical": resolution.missing_critical,
        "conflicts": resolution.conflicts,
        "explanation": resolution.explanation,
    }


def prompt_lint(
    session: Session,
    prompt_text: str,
    project_types: list[str],
    changed_paths: list[str] | None = None,
    risk_labels: list[str] | None = None,
):
    result = RuleRelevanceService().lint_prompt(
        prompt_text,
        project_types,
        changed_paths=changed_paths,
        risk_labels=risk_labels,
    )
    return result.machine


def sync_next_actions(session: Session, project_types: list[str]):
    return RuleRelevanceService().sync_next_actions(project_types)
