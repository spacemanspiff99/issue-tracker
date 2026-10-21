from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from issue_tracker.db import get_session
from issue_tracker.domain.enums import IssueStatus
from issue_tracker.domain.models import Issue
from issue_tracker.services.tracker import IssueService
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

    sprint = client.post(f"{project_path}/sprints", data={"goal": "MVP"}, follow_redirects=False)
    assert sprint.status_code == 303
    sprint_path = sprint.headers["location"]
    added = client.post(f"{sprint_path}/issues", data={"issue_id": blocked.id})
    assert added.status_code == 200
    assert "Blocked" in added.text

    closed = client.post(
        f"/issues/{blocked.id}/close",
        data={"originating_llm": "gpt-5.5", "close_note": "done"},
        follow_redirects=False,
    )
    assert closed.status_code == 303

    project_page = client.get(project_path)
    assert "done" in project_page.text
    assert "Issue log" in project_page.text


def _project_with_issues(client, maker, name="Tracker", titles=("Blocker", "Blocked")):
    project = client.post("/projects", data={"name": name, "repo_url": ""}, follow_redirects=False)
    project_path = project.headers["location"]
    for title in titles:
        client.post(f"{project_path}/issues", data={"title": title, "acceptance_criteria": f"- [ ] {title}"})
    project_id = int(project_path.rsplit("/", 1)[1])
    with maker() as session:
        issues = session.query(Issue).filter_by(project_id=project_id).order_by(Issue.sequence).all()
    return project_path, issues


def test_project_and_category_domain_errors_render_inline(engine):
    client, _ = make_client(engine)
    client.post("/setup", data={"username": "admin", "password": "secret"})

    blank_project = client.post("/projects", data={"name": "   ", "repo_url": ""})
    assert blank_project.status_code == 400
    assert "Project name is required" in blank_project.text

    project_path = client.post("/projects", data={"name": "Tracker"}, follow_redirects=False).headers["location"]
    blank_category = client.post(
        f"{project_path}/categories", data={"key": "BUG", "name": "Bug", "checklist": "   "}
    )
    assert blank_category.status_code == 400
    assert "Category key, name, and checklist are required" in blank_category.text

    blank_sprint = client.post(f"{project_path}/sprints", data={"goal": "   "})
    assert blank_sprint.status_code == 400
    assert "Sprint goal is required" in blank_sprint.text


def test_dependency_domain_errors_render_inline_on_issue_page(engine):
    client, maker = make_client(engine)
    client.post("/setup", data={"username": "admin", "password": "secret"})
    _, (blocker, blocked) = _project_with_issues(client, maker)
    client.post(f"/issues/{blocked.id}/dependencies", data={"blocker_issue_id": blocker.id})

    cycle = client.post(f"/issues/{blocker.id}/dependencies", data={"blocker_issue_id": blocked.id})
    assert cycle.status_code == 400
    assert "Dependency would create a cycle" in cycle.text
    assert f"{blocked.id} blocks {blocker.id}" not in cycle.text

    duplicate = client.post(f"/issues/{blocked.id}/dependencies", data={"blocker_issue_id": blocker.id})
    assert duplicate.status_code == 400
    assert "Dependency already exists" in duplicate.text

    self_edge = client.post(f"/issues/{blocked.id}/dependencies", data={"blocker_issue_id": blocked.id})
    assert self_edge.status_code == 400
    assert "An issue cannot block itself" in self_edge.text


def test_close_domain_errors_render_inline_and_metadata_is_shown(engine):
    client, maker = make_client(engine)
    client.post("/setup", data={"username": "admin", "password": "secret"})
    _, (issue,) = _project_with_issues(client, maker, titles=("Closable",))

    blank = client.post(f"/issues/{issue.id}/close", data={"originating_llm": "   ", "close_note": ""})
    assert blank.status_code == 400
    assert "Originating LLM is required to close an issue" in blank.text
    assert "Status: backlog" in blank.text

    closed = client.post(
        f"/issues/{issue.id}/close",
        data={"originating_llm": "gpt-5.5", "close_note": "first"},
        follow_redirects=False,
    )
    assert closed.status_code == 303
    detail = client.get(f"/issues/{issue.id}")
    assert "<dd>gpt-5.5</dd>" in detail.text
    assert "<dd>admin</dd>" in detail.text
    assert "<dd>first</dd>" in detail.text

    reclose = client.post(f"/issues/{issue.id}/close", data={"originating_llm": "other-llm", "close_note": "x"})
    assert reclose.status_code == 400
    assert "Closed issue metadata is immutable" in reclose.text
    assert "<dd>gpt-5.5</dd>" in reclose.text
    assert "other-llm" not in reclose.text


def test_sprint_issue_domain_error_renders_inline(engine):
    client, maker = make_client(engine)
    client.post("/setup", data={"username": "admin", "password": "secret"})
    project_path, _ = _project_with_issues(client, maker, name="One", titles=("Mine",))
    _, (foreign,) = _project_with_issues(client, maker, name="Two", titles=("Foreign",))
    sprint_path = client.post(f"{project_path}/sprints", data={"goal": "MVP"}, follow_redirects=False).headers[
        "location"
    ]

    cross = client.post(f"{sprint_path}/issues", data={"issue_id": foreign.id})
    assert cross.status_code == 400
    assert "Sprint and issue belong to different projects" in cross.text


def test_sprint_add_closed_issue_renders_inline_error_and_keeps_it_closed(engine):
    client, maker = make_client(engine)
    client.post("/setup", data={"username": "admin", "password": "secret"})
    project_path, (closed,) = _project_with_issues(client, maker, titles=("Closed",))
    with maker() as session:
        IssueService(session).update_status(closed.id, "done", originating_llm="gpt-5.5")
    sprint_path = client.post(f"{project_path}/sprints", data={"goal": "MVP"}, follow_redirects=False).headers[
        "location"
    ]

    added = client.post(f"{sprint_path}/issues", data={"issue_id": closed.id})
    assert added.status_code == 400
    assert "Closed issue cannot be added to a sprint" in added.text
    with maker() as session:
        issue = session.get(Issue, closed.id)
        assert issue.status == IssueStatus.DONE
        assert issue.closed_at is not None
