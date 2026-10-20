"""Deterministic demo data for local manual UAT (`issue-tracker seed-demo`).

Everything goes through the service layer. The command only ever creates one new project; it
never deletes, truncates, or migrates. Re-running with an existing project name is a no-op.
"""

from __future__ import annotations

import argparse
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from issue_tracker.domain.models import Project
from issue_tracker.services.tracker import (
    CategoryService,
    IssueLogService,
    IssueService,
    ProjectService,
    SprintService,
    display_id,
)

DEFAULT_PROJECT_NAME = "UAT Demo"
DEMO_LLM = "demo-seed"

# Demo-only taxonomy, created as data in the demo project (not a built-in taxonomy).
CATEGORIES = [
    ("DEMO-STATE", "Demo state integrity", "- [ ] Sequence, status, and close metadata are correct"),
    ("DEMO-UI", "Demo browser checks", "- [ ] Page is styled and usable on desktop and mobile"),
]


def seed_demo(session: Session, project_name: str = DEFAULT_PROJECT_NAME) -> dict[str, object]:
    existing = session.scalar(select(Project).where(Project.name == project_name.strip()))
    if existing is not None:
        return {"created": False, "project_id": existing.id, "project": existing.name}

    project = ProjectService(session).create_project(project_name)
    categories = {
        key: CategoryService(session).create_category(project.id, key, name, checklist)
        for key, name, checklist in CATEGORIES
    }
    issues = IssueService(session)
    blocker = issues.create_issue(
        project.id,
        "Demo blocker issue",
        "- [ ] Blocks the demo blocked issue",
        category_id=categories["DEMO-STATE"].id,
    )
    blocked = issues.create_issue(
        project.id,
        "Demo blocked issue",
        "- [ ] Waits on the demo blocker issue",
        category_id=categories["DEMO-STATE"].id,
    )
    closed = issues.create_issue(
        project.id,
        "Demo closed issue",
        "- [ ] Closed with originating LLM metadata",
        category_id=categories["DEMO-UI"].id,
    )
    issues.add_dependency(blocker.id, blocked.id)
    sprint = SprintService(session).create_sprint(project.id, "Demo UAT sprint")
    SprintService(session).add_issue(sprint.id, blocked.id)
    # Created after the sprint so the shared NNNN sequence shows issue/sprint interleaving.
    backlog = issues.create_issue(project.id, "Demo backlog issue", "- [ ] Stays in backlog")
    issues.update_status(closed.id, "done", originating_llm=DEMO_LLM, closed_by="seed-demo", close_note="Demo close")
    IssueLogService(session).create_entry(
        project.id,
        "Demo root cause",
        "Demo prevention added",
        issue_id=closed.id,
        category_id=categories["DEMO-UI"].id,
    )
    return {
        "created": True,
        "project_id": project.id,
        "project": project.name,
        "categories": list(categories),
        "issues": {display_id(i.sequence): i.title for i in (blocker, blocked, closed, backlog)},
        "sprint": display_id(sprint.sequence),
    }


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project-name", default=DEFAULT_PROJECT_NAME)


def run(session: Session, args: argparse.Namespace) -> None:
    print(json.dumps(seed_demo(session, args.project_name), sort_keys=True))
