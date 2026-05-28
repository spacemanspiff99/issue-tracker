from __future__ import annotations

import io
import json
import logging

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from issue_tracker.db import get_session
from issue_tracker.domain.models import Issue
from issue_tracker.logging import JsonFormatter
from issue_tracker.services.guidance_sync import GuidanceSyncService
from issue_tracker.services.tracker import IssueLogService
from issue_tracker.web.app import create_app


def make_client(engine):
    maker = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    app = create_app()

    def override_session():
        with maker() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    return TestClient(app), maker


def test_setup_login_and_issue_validation_path(engine):
    client, _ = make_client(engine)

    setup = client.post("/setup", data={"username": "admin", "password": "secret"}, follow_redirects=False)
    assert setup.status_code == 303
    assert "session=" in setup.headers["set-cookie"]
    assert "httponly" in setup.headers["set-cookie"].lower()
    assert "samesite=lax" in setup.headers["set-cookie"].lower()

    project = client.post("/projects", data={"name": "Tracker", "repo_url": ""}, follow_redirects=False)
    assert project.status_code == 303
    project_path = project.headers["location"]

    missing_ac = client.post(f"{project_path}/issues", data={"title": "No AC", "acceptance_criteria": ""})
    assert missing_ac.status_code == 400
    assert "Acceptance criteria are required" in missing_ac.text

    created = client.post(f"{project_path}/issues", data={"title": "Has AC", "acceptance_criteria": "- [ ] pass"})
    assert created.status_code == 200
    assert "Has AC" in created.text


def test_login_errors_and_rate_limit_are_visible(engine):
    client, _ = make_client(engine)
    client.post("/setup", data={"username": "admin", "password": "secret"}, follow_redirects=False)
    client.post("/logout", follow_redirects=False)

    invalid = client.post("/login", data={"username": "admin", "password": "wrong"})
    assert invalid.status_code == 400
    assert "Invalid login" in invalid.text

    for _ in range(6):
        limited = client.post("/login", data={"username": "limited-user", "password": "wrong"})

    assert limited.status_code == 429
    assert "Too many attempts" in limited.text


def test_request_logging_uses_route_template_without_query_payload(engine):
    client, _ = make_client(engine)
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(
        JsonFormatter(app="issue-tracker", service="app", source="app-log", environment="test")
    )
    logger = logging.getLogger("issue_tracker.web")
    old_handlers = logger.handlers[:]
    old_level = logger.level
    old_propagate = logger.propagate
    try:
        logger.handlers = [handler]
        logger.setLevel(logging.INFO)
        logger.propagate = False

        response = client.get("/login?password=secret&token=abc")

        assert response.status_code == 200
        lines = [json.loads(line) for line in stream.getvalue().splitlines()]
        request_log = next(entry for entry in lines if entry.get("event") == "http_request")
        assert request_log["method"] == "GET"
        assert request_log["route"] == "/login"
        assert request_log["status_code"] == 200
        assert "password" not in stream.getvalue()
        assert "token" not in stream.getvalue()
        assert "secret" not in stream.getvalue()
    finally:
        logger.handlers = old_handlers
        logger.setLevel(old_level)
        logger.propagate = old_propagate


def test_project_page_validation_errors_preserve_context(engine):
    client, _ = make_client(engine)
    client.post("/setup", data={"username": "admin", "password": "secret"})
    project = client.post("/projects", data={"name": "Tracker", "repo_url": ""}, follow_redirects=False)
    project_path = project.headers["location"]

    created_category = client.post(
        f"{project_path}/categories",
        data={"key": "IT-1", "name": "Tracker State", "checklist": "Verify tracker state"},
        follow_redirects=False,
    )
    assert created_category.status_code == 303

    duplicate_category = client.post(
        f"{project_path}/categories",
        data={"key": "IT-1", "name": "Duplicate", "checklist": "Verify duplicate handling"},
        follow_redirects=False,
    )
    blank_sprint = client.post(f"{project_path}/sprints", data={"goal": ""}, follow_redirects=False)

    assert duplicate_category.status_code == 400
    assert "Category violates a unique constraint" in duplicate_category.text
    assert "Tracker State" in duplicate_category.text
    assert blank_sprint.status_code == 400
    assert "Sprint goal is required" in blank_sprint.text
    assert "Tracker State" in blank_sprint.text


def test_project_archive_hides_uat_clutter_without_deleting(engine):
    client, _ = make_client(engine)
    client.post("/setup", data={"username": "admin", "password": "secret"})
    project = client.post("/projects", data={"name": "Browser UAT Project", "repo_url": ""}, follow_redirects=False)
    project_id = int(project.headers["location"].rsplit("/", 1)[-1])

    archived = client.post(f"/projects/{project_id}/active", data={"active": "false"}, follow_redirects=False)
    hidden = client.get("/")
    visible_with_archived = client.get("/search?show_all=true")
    restored = client.post(f"/projects/{project_id}/active", data={"active": "true"}, follow_redirects=False)
    visible = client.get("/")

    assert archived.status_code == 303
    assert "Browser UAT Project" not in hidden.text
    assert "Browser UAT Project" in visible_with_archived.text
    assert "archived" in visible_with_archived.text
    assert restored.status_code == 303
    assert "Browser UAT Project" in visible.text


def test_web_mvp_project_issue_dependency_sprint_close_flow(engine):
    client, maker = make_client(engine)
    client.post("/setup", data={"username": "admin", "password": "secret"})
    project = client.post("/projects", data={"name": "Tracker", "repo_url": ""}, follow_redirects=False)
    project_path = project.headers["location"]
    client.post(f"{project_path}/issues", data={"title": "Blocker", "acceptance_criteria": "- [ ] blocker"})
    client.post(f"{project_path}/issues", data={"title": "Blocked", "acceptance_criteria": "- [ ] blocked"})

    with maker() as session:
        issues = session.query(Issue).order_by(Issue.sequence).all()
        blocker, blocked = issues

    dependency = client.post(
        f"/issues/{blocked.id}/dependencies",
        data={"blocker_issue_id": blocker.id},
        follow_redirects=False,
    )
    assert dependency.status_code == 303

    sprint = client.post(
        f"{project_path}/sprints",
        data={"goal": "MVP", "context": "Build the MVP slice and run route tests."},
        follow_redirects=False,
    )
    assert sprint.status_code == 303
    sprint_path = sprint.headers["location"]
    refreshed_project = client.get(project_path)
    assert "MVP" in refreshed_project.text
    assert sprint_path in refreshed_project.text
    assert "Workflow command center" in refreshed_project.text
    assert "Blocked work" in refreshed_project.text
    assert "0002 Blocked" in refreshed_project.text
    assert "0001 Blocker" in refreshed_project.text
    sprint_page = client.get(sprint_path)
    assert "Build the MVP slice and run route tests." in sprint_page.text
    added = client.post(f"{sprint_path}/issues", data={"issue_id": blocked.id})
    assert added.status_code == 200
    assert "Blocked" in added.text
    assert "in-progress" in added.text

    closed = client.post(
        f"/issues/{blocked.id}/close",
        data={"originating_llm": "gpt-5.5", "close_note": "done"},
        follow_redirects=False,
    )
    assert closed.status_code == 303

    with maker() as session:
        IssueLogService(session).create_agent_failure(
            project_id=blocked.project_id,
            target="complete workflow",
            observed_failure="missed close evidence",
            prevention_added="Show linked issue-log records on issue detail.",
            issue_id=blocked.id,
            severity="high",
        )

    issue_page = client.get(f"/issues/{blocked.id}")
    assert "Originating LLM" in issue_page.text
    assert "gpt-5.5" in issue_page.text
    assert "Closed by" in issue_page.text
    assert "admin" in issue_page.text
    assert "done" in issue_page.text
    assert "Issue log records" in issue_page.text
    assert "agent-failure" in issue_page.text

    project_page = client.get(project_path)
    assert "done" in project_page.text
    assert "Issue log" in project_page.text
    assert "Guidance Sync" in project_page.text

    with maker() as session:
        guidance = GuidanceSyncService(session)
        source = guidance.configure_source(blocked.project_id, "Tracker", "local", ["AGENTS.md"])
        guidance.classify_drift(blocked.project_id, "AGENTS.md", source_id=source.id, left_hash="a", right_hash="b")
    guidance_page = client.get(f"{project_path}/guidance-sync")
    assert guidance_page.status_code == 200
    assert "Tracker Guidance Sync" in guidance_page.text
    assert "AGENTS.md" in guidance_page.text
    assert "Harnesses" in guidance_page.text


def test_dependency_cycle_error_is_rendered_on_issue_page(engine):
    client, maker = make_client(engine)
    client.post("/setup", data={"username": "admin", "password": "secret"})
    project = client.post("/projects", data={"name": "Tracker", "repo_url": ""}, follow_redirects=False)
    project_path = project.headers["location"]
    client.post(f"{project_path}/issues", data={"title": "First", "acceptance_criteria": "- [ ] first"})
    client.post(f"{project_path}/issues", data={"title": "Second", "acceptance_criteria": "- [ ] second"})

    with maker() as session:
        issues = session.query(Issue).order_by(Issue.sequence).all()
        first, second = issues

    client.post(
        f"/issues/{second.id}/dependencies",
        data={"blocker_issue_id": first.id},
        follow_redirects=False,
    )
    dependency_page = client.get(f"/issues/{second.id}")
    cycle = client.post(
        f"/issues/{first.id}/dependencies",
        data={"blocker_issue_id": second.id},
        follow_redirects=False,
    )

    assert "Issue 0001: First" in dependency_page.text
    assert "blocks Issue 0002: Second" in dependency_page.text
    assert cycle.status_code == 400
    assert "Dependency would create a cycle" in cycle.text
    assert "Issue 0001: First" in cycle.text


def test_duplicate_sprint_assignment_error_is_rendered_on_sprint_page(engine):
    client, maker = make_client(engine)
    client.post("/setup", data={"username": "admin", "password": "secret"})
    project = client.post("/projects", data={"name": "Tracker", "repo_url": ""}, follow_redirects=False)
    project_path = project.headers["location"]
    client.post(f"{project_path}/issues", data={"title": "Assigned", "acceptance_criteria": "- [ ] assigned"})
    sprint = client.post(f"{project_path}/sprints", data={"goal": "MVP"}, follow_redirects=False)
    sprint_path = sprint.headers["location"]

    with maker() as session:
        issue = session.query(Issue).one()

    first_add = client.post(f"{sprint_path}/issues", data={"issue_id": issue.id}, follow_redirects=False)
    duplicate_add = client.post(f"{sprint_path}/issues", data={"issue_id": issue.id}, follow_redirects=False)

    assert first_add.status_code == 303
    assert duplicate_add.status_code == 400
    assert "Sprint membership violates a database invariant" in duplicate_add.text
    assert "Assigned" in duplicate_add.text


def test_saved_views_search_backlog_board_and_inline_updates(engine):
    client, maker = make_client(engine)
    client.post("/setup", data={"username": "admin", "password": "secret"})
    project = client.post(
        "/projects",
        data={"name": "Tracker", "repo_url": "https://example.test/repo"},
        follow_redirects=False,
    )
    project_path = project.headers["location"]
    client.post(f"{project_path}/issues", data={"title": "Backlog item", "acceptance_criteria": "- [ ] backlog"})
    client.post(f"{project_path}/issues", data={"title": "Active item", "acceptance_criteria": "- [ ] active"})

    search = client.get("/search?q=Tracker")
    assert search.status_code == 200
    assert "https://example.test/repo" in search.text

    with maker() as session:
        issues = session.query(Issue).order_by(Issue.sequence).all()
        backlog, active = issues

    client.post(f"/issues/{active.id}/status", data={"status": "in-progress", "priority": "high"})
    backlog_view = client.get(f"{project_path}/backlog")
    not_in_sprint_view = client.get(f"{project_path}/backlog?view=not-in-sprint")
    done_view = client.get(f"{project_path}/backlog?view=done")
    board_view = client.get(f"{project_path}/board")
    filtered = client.get(f"{project_path}?view=backlog&q=Backlog")

    assert "Saved views" in backlog_view.text
    assert "/projects/1/backlog?view=not-in-sprint" in backlog_view.text
    assert "Issues Not In Sprint" in backlog_view.text
    assert "Backlog order" in backlog_view.text
    assert "draggable" in backlog_view.text
    assert "Active item" in not_in_sprint_view.text
    assert "Backlog item" in not_in_sprint_view.text
    assert "No issues found for the done saved view" in done_view.text
    assert "Tracker Sprint Board" in board_view.text
    assert "Active item" in board_view.text
    assert "Backlog item" in filtered.text
    assert "Active item" not in filtered.text

    reorder = client.post(
        f"{project_path}/backlog/reorder",
        data={"ordered_issue_ids": f"{active.id},{backlog.id}"},
        follow_redirects=False,
    )
    assert reorder.status_code == 303


def test_release_intake_sprint_assignment_and_board_filters(engine):
    client, maker = make_client(engine)
    client.post("/setup", data={"username": "admin", "password": "secret"})
    project = client.post("/projects", data={"name": "Tracker", "repo_url": ""}, follow_redirects=False)
    project_path = project.headers["location"]
    client.post(f"{project_path}/issues", data={"title": "Release item", "acceptance_criteria": "- [ ] release"})
    client.post(f"{project_path}/issues", data={"title": "Later item", "acceptance_criteria": "- [ ] later"})
    sprint = client.post(f"{project_path}/sprints", data={"goal": "MVP release"}, follow_redirects=False)
    sprint_path = sprint.headers["location"]

    with maker() as session:
        issues = session.query(Issue).order_by(Issue.sequence).all()
        first, second = issues
        sprint_id = int(sprint_path.rsplit("/", 1)[-1])

    metadata = client.post(
        f"/issues/{first.id}/metadata",
        data={
            "labels": "release",
            "story": "Release planning",
            "delivery_phase": "Gate",
            "milestone": "MVP release",
            "custom_fields": "readiness=tests pending",
        },
        follow_redirects=False,
    )
    assigned = client.post(f"/issues/{first.id}/sprints", data={"sprint_id": sprint_id}, follow_redirects=False)
    workflow = client.post(f"/issues/{second.id}/workflow", data={"workflow_state": "clarify"}, follow_redirects=False)
    releases = client.get(f"{project_path}/releases")
    release_drilldown = client.get(f"{project_path}/backlog?view=all&milestone=MVP%20release")
    board = client.get(f"{project_path}/board?sprint_id={sprint_id}")
    categories = client.get(f"{project_path}/categories")
    sprints = client.get(f"{project_path}/sprints")

    assert metadata.status_code == 303
    assert assigned.status_code == 303
    assert workflow.status_code == 303
    assert "MVP release" in releases.text
    assert "tests pending" in releases.text
    assert "Current" in releases.text
    assert "1 total" in releases.text
    assert "Release item" in release_drilldown.text
    assert "Later item" not in release_drilldown.text
    assert "Release item" in board.text
    assert "Later item" in board.text
    assert "Assign backlog to sprint" in board.text
    assert "Categories" in categories.text
    assert "Uncategorized" in categories.text
    assert "Sprints" in sprints.text
    assert "MVP release" in sprints.text

    intake = client.post(
        f"{project_path}/voice-feedback",
        data={"title": "Audio bug", "notes": "Button failed", "priority": "high", "ambiguous": "true"},
        files={"audio": ("feedback.webm", b"fake audio", "audio/webm")},
        follow_redirects=False,
    )
    urgent_audio_only = client.post(
        f"{project_path}/voice-feedback",
        data={"title": "", "notes": "", "priority": "urgent"},
        files={"audio": ("urgent.webm", b"urgent fake audio", "audio/webm")},
        follow_redirects=False,
    )
    autosave = client.post(
        f"{project_path}/voice-feedback",
        data={"autosave": "true", "title": "", "notes": "", "priority": ""},
        files={"audio": ("autosave.webm", b"autosaved fake audio", "audio/webm")},
    )
    autosave_payload = autosave.json()
    delete_autosave = client.post(f"/issues/{autosave_payload['issue_id']}/voice-intake/delete")
    intake_page = client.get(f"{project_path}/intake")

    assert intake.status_code == 303
    assert urgent_audio_only.status_code == 303
    assert autosave.status_code == 200
    assert autosave_payload["ok"] is True
    assert autosave_payload["title"] == "Voice feedback: To process: audio note"
    assert delete_autosave.status_code == 200
    assert delete_autosave.json()["ok"] is True
    assert "Record audio" in intake_page.text
    assert "Upload audio file" in intake_page.text
    assert "Voice feedback: Audio bug" in intake_page.text
    assert "Voice feedback: To process: urgent audio note" in intake_page.text
    assert "Needs clarification" in intake_page.text
    assert "Needs clarification" in client.get(f"/issues/{second.id}").text


def test_issue_edit_metadata_comments_references_and_docs_surfaces(engine):
    client, maker = make_client(engine)
    client.post("/setup", data={"username": "admin", "password": "secret"})
    project = client.post("/projects", data={"name": "Tracker", "repo_url": ""}, follow_redirects=False)
    project_path = project.headers["location"]
    client.post(
        f"{project_path}/categories",
        data={"key": "UI", "name": "User Interface", "checklist": "Review rendered forms"},
    )
    client.post(f"{project_path}/issues", data={"title": "Editable", "acceptance_criteria": "- [ ] old"})

    with maker() as session:
        issue = session.query(Issue).one()

    edit = client.post(
        f"/issues/{issue.id}/edit",
        data={
            "title": "Edited",
            "acceptance_criteria": "- [ ] new",
            "priority": "high",
            "summary": "Updated summary",
            "proposed_approach": "Use forms",
            "status": "in-progress",
        },
        follow_redirects=False,
    )
    metadata = client.post(
        f"/issues/{issue.id}/metadata",
        data={
            "labels": "ui, sprint",
            "story": "Modern UI",
            "delivery_phase": "Build",
            "milestone": "MVP",
            "custom_fields": "risk=low",
        },
        follow_redirects=False,
    )
    comment = client.post(
        f"/issues/{issue.id}/comments",
        data={"message": "Browser UAT needed"},
        follow_redirects=False,
    )
    reference = client.post(
        f"/issues/{issue.id}/references",
        data={"repo": "owner/repo", "url": "https://github.com/owner/repo/pull/1", "pr_number": "1"},
        follow_redirects=False,
    )
    cancelled = client.post(
        f"/issues/{issue.id}/edit",
        data={
            "title": "Edited",
            "acceptance_criteria": "- [ ] new",
            "priority": "high",
            "summary": "Updated summary",
            "proposed_approach": "Use forms",
            "status": "cancelled",
        },
        follow_redirects=False,
    )
    page = client.get(f"/issues/{issue.id}")
    planning = client.get(f"{project_path}/planning")
    backup = client.get(f"{project_path}/backup")

    assert edit.status_code == 303
    assert metadata.status_code == 303
    assert comment.status_code == 303
    assert reference.status_code == 303
    assert cancelled.status_code == 303
    assert "Edited" in page.text
    assert "cancelled" in page.text
    assert "Cancelled or marked won&#39;t do from web status control." in page.text
    assert "Modern UI" in page.text
    assert "Browser UAT needed" in page.text
    assert "owner/repo#1" in page.text
    assert "Markdown import plan" in planning.text
    assert "export-recovery-bundle" in backup.text
    assert "export-json" in backup.text
