from __future__ import annotations

import json

from issue_tracker.cli import export_json
from issue_tracker.demo_data import seed_demo
from issue_tracker.domain.models import Issue, Project
from issue_tracker.mcp import tools
from issue_tracker.services.tracker import IssueService, ProjectService


def test_seed_demo_is_deterministic_and_shows_shared_sequence(session):
    result = seed_demo(session)

    assert result["created"] is True
    assert result["issues"] == {
        "0001": "Demo blocker issue",
        "0002": "Demo blocked issue",
        "0003": "Demo closed issue",
        "0005": "Demo backlog issue",
    }
    assert result["sprint"] == "0004"
    issue_id = IssueService(session).get_issue_by_sequence(result["project_id"], 3).id
    closed = tools.issue_get(session, issue_id, include_full=True)["issue"]
    assert closed["status"] == "done"
    assert closed["originating_llm"] == "demo-seed"


def test_seed_demo_rerun_is_a_noop(session):
    first = seed_demo(session)
    second = seed_demo(session)

    assert second == {"created": False, "project_id": first["project_id"], "project": "UAT Demo"}
    assert session.query(Project).count() == 1
    assert session.query(Issue).count() == 4


def test_seed_demo_leaves_other_projects_untouched(session):
    other = ProjectService(session).create_project("Existing")
    result = seed_demo(session, "Second Demo")

    assert result["project_id"] != other.id
    assert session.query(Issue).filter_by(project_id=other.id).count() == 0


def test_seed_demo_export_is_secret_free(session, tmp_path):
    project_id = seed_demo(session)["project_id"]
    output = tmp_path / "demo.json"

    export_json(session, project_id, output)

    serialized = output.read_text()
    assert json.loads(serialized)["project"]["name"] == "UAT Demo"
    for forbidden in ("password", "APP_SECRET_KEY", "session", "DATABASE_URL"):
        assert forbidden not in serialized
