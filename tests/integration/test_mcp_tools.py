from __future__ import annotations

import pytest

from issue_tracker.mcp import server, tools
from issue_tracker.services.tracker import DomainError, IssueService, ProjectService


def test_mcp_compact_outputs_do_not_dump_acceptance_criteria_by_default(session):
    project = ProjectService(session).create_project("Tracker")
    issue = IssueService(session).create_issue(project.id, "Compact", "- [ ] hidden by default")

    search = tools.issue_search(session, project_id=project.id)
    compact = tools.issue_get(session, issue.id)
    full = tools.issue_get(session, issue.id, include_full=True)

    assert "acceptance_criteria" not in search["issues"][0]
    assert "acceptance_criteria" not in compact["issue"]
    assert full["issue"]["acceptance_criteria"] == "- [ ] hidden by default"


def test_mcp_mutating_path_uses_services(session):
    project = ProjectService(session).create_project("Tracker")
    created = tools.issue_create(session, project.id, "From MCP", "- [ ] created")
    updated = tools.issue_update_status(session, created["issue"]["id"], "done", originating_llm="gpt-5.5")

    assert created["issue"]["sequence"] == "0001"
    assert updated["issue"]["status"] == "done"
    assert updated["closed_at"] is not None


def test_mcp_smoke_lists_expected_tools():
    result = server.smoke()

    assert result["ok"] is True
    assert "issue.create" in result["tools"]
    assert "next_action" in result["tools"]


def test_mcp_sprint_add_rejects_closed_issue_like_web(session):
    project = ProjectService(session).create_project("Tracker")
    sprint = tools.sprint_create(session, project.id, "MVP")["sprint"]
    created = tools.issue_create(session, project.id, "Closed", "- [ ] closed")["issue"]
    tools.issue_update_status(session, created["id"], "done", originating_llm="gpt-5.5")

    with pytest.raises(DomainError, match="Closed issue cannot be added to a sprint"):
        tools.sprint_add_issue(session, sprint["id"], created["id"])
    issue = tools.issue_get(session, created["id"])["issue"]
    assert issue["status"] == "done"
