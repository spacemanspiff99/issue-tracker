from __future__ import annotations

from issue_tracker.mcp import server, tools
from issue_tracker.services.guidance_sync import GuidanceSyncService
from issue_tracker.services.recovery_bundle import RecoveryBundleService
from issue_tracker.services.tracker import CategoryService, IssueService, ProjectService


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
    updated = tools.issue_update_status(
        session,
        created["issue"]["id"],
        "done",
        originating_llm="gpt-5.5",
        closed_by="mcp-smoke",
        close_note="verified",
    )
    full = tools.issue_get(session, created["issue"]["id"], include_full=True)

    assert created["issue"]["sequence"] == "0001"
    assert "next" in created
    assert updated["issue"]["status"] == "done"
    assert updated["closed_at"] is not None
    assert "next" in updated
    assert full["issue"]["closed_by"] == "mcp-smoke"
    assert full["issue"]["close_note"] == "verified"


def test_mcp_dependency_sprint_category_and_next_action_paths_are_compact(session):
    project = ProjectService(session).create_project("Tracker")
    CategoryService(session).create_category(project.id, "IT-1", "Tracker State", "Verify tracker state")
    blocker = IssueService(session).create_issue(project.id, "Blocker", "- [ ] blocker")
    blocked = IssueService(session).create_issue(project.id, "Blocked", "- [ ] blocked")

    categories = tools.category_list(session, project.id)
    dependency = tools.issue_add_dependency(session, blocker.id, blocked.id)
    sprint = tools.sprint_create(session, project.id, "MCP sprint", "compact test")
    membership = tools.sprint_add_issue(session, sprint["sprint"]["id"], blocked.id)
    fetched = tools.sprint_get(session, sprint["sprint"]["id"])
    action = tools.next_action(session, project.id)

    assert categories["categories"] == [{"id": 1, "key": "IT-1", "name": "Tracker State"}]
    assert dependency["dependency"]["status"] == "created"
    assert "next" in dependency
    assert sprint["sprint"]["status"] == "active"
    assert "next" in sprint
    assert membership["sprint_issue"]["status"] == "todo"
    assert "next" in membership
    assert fetched["issues"][0]["title"] == "Blocked"
    assert "acceptance_criteria" not in fetched["issues"][0]
    assert action["active_sprint_id"] == sprint["sprint"]["id"]


def test_mcp_issue_search_uses_shared_saved_views(session):
    project = ProjectService(session).create_project("Tracker")
    blocker = IssueService(session).create_issue(project.id, "Blocker", "- [ ] blocker")
    blocked = IssueService(session).create_issue(project.id, "Blocked", "- [ ] blocked")
    IssueService(session).add_dependency(blocker.id, blocked.id)

    result = tools.issue_search(session, project_id=project.id, view="blocked")

    assert result["issues"] == [
        {"id": blocked.id, "sequence": "0002", "title": "Blocked", "status": "backlog", "priority": "normal"}
    ]


def test_mcp_guidance_sync_tools_are_compact(session):
    project = ProjectService(session).create_project("Tracker")
    issue = IssueService(session).create_issue(project.id, "Repair guidance", "- [ ] verified")
    guidance = GuidanceSyncService(session)
    source = guidance.configure_source(project.id, "Tracker", "local", ["AGENTS.md"])
    drift = guidance.classify_drift(project.id, "AGENTS.md", source_id=source.id, left_hash="a", right_hash="b")

    health = tools.guidance_sync_health(session, project.id)
    drifts = tools.guidance_sync_drift_list(session, project.id)
    proposal = tools.guidance_sync_create_proposal(
        session,
        project.id,
        drift.id,
        "merge-needed",
        issue.id,
        "codex",
        "python -m pytest tests/integration/test_mcp_tools.py",
    )

    assert health["open_drift"] == 1
    assert "next" in health
    assert drifts["drifts"] == [
        {
            "id": drift.id,
            "path": "AGENTS.md",
            "type": "stale",
            "severity": "normal",
            "recommended_action": "merge-needed",
        }
    ]
    assert proposal["proposal"]["status"] == "draft"


def test_mcp_backup_health_is_compact(session, tmp_path):
    project = ProjectService(session).create_project("Tracker")
    IssueService(session).create_issue(project.id, "Backed up", "- [ ] backed up")
    RecoveryBundleService(session).export_bundle(project.id, tmp_path / "tracker" / "latest")

    missing = tools.backup_health(session, project.id)
    explicit = RecoveryBundleService(session).backup_health(project.id, tmp_path)

    assert missing["status"] == "missing"
    assert "next" in missing
    assert explicit["status"] == "verified"
    assert explicit["counts"]["issues"] == 1


def test_mcp_backup_rule_and_prompt_contracts_are_compact(session):
    project = ProjectService(session).create_project("Issue Tracker")

    backup_plan = tools.backup_vibecoding_plan(session, project.id)
    artifact = tools.backup_artifact_check(session, ["exports/voice-feedback/raw.webm"])
    rules = tools.rule_resolve(
        session,
        ["fastapi-jinja-postgres", "mcp-server"],
        changed_paths=["src/issue_tracker/mcp/tools.py"],
        risk_labels=["mcp", "backup"],
    )
    lint = tools.prompt_lint(
        session,
        "# Prompt\n\nRecommended model/reasoning: GPT-5.5 high\n\n## Acceptance Criteria\n- [ ] done\n",
        ["fastapi-jinja-postgres"],
        changed_paths=["migrations/versions/0004.py"],
        risk_labels=["schema"],
    )
    next_actions = tools.sync_next_actions(session, ["fastapi-jinja-postgres"])

    assert backup_plan["latest"] == "projects/issue-tracker/tracker-backups/latest"
    assert artifact["status"] in {"blocked", "ready"}
    assert "backup-safety" in [rule["rule_id"] for rule in rules["rules"]]
    assert lint["status"] == "block"
    assert "next" in next_actions


def test_mcp_smoke_lists_expected_tools():
    result = server.smoke()

    assert result["ok"] is True
    assert "issue.create" in result["tools"]
    assert "next_action" in result["tools"]
    assert "guidance_sync.health" in result["tools"]
    assert "backup.health" in result["tools"]
    assert "backup.vibecoding_plan" in result["tools"]
    assert "backup.artifact_check" in result["tools"]
    assert "rule.resolve" in result["tools"]
    assert "prompt.lint" in result["tools"]
    assert "sync.next_actions" in result["tools"]
