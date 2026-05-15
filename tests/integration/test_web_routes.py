from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from issue_tracker.db import get_session
from issue_tracker.domain.models import Issue
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
