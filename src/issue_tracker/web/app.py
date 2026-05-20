from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware
from starlette.status import HTTP_303_SEE_OTHER

from issue_tracker.config import get_settings
from issue_tracker.db import check_database, get_session
from issue_tracker.repositories.store import Repository
from issue_tracker.services.tracker import (
    AuthService,
    CategoryService,
    DomainError,
    IssueLogService,
    IssueService,
    ProjectService,
    SprintService,
    display_id,
)
from issue_tracker.web.security import (
    clear_failed_login,
    hash_password,
    login_limited,
    note_failed_login,
    require_user,
    verify_password,
)

templates = Jinja2Templates(directory=str(Path(__file__).with_name("templates")))
templates.env.globals["display_id"] = display_id


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Issue Tracker")
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.app_secret_key,
        https_only=settings.session_cookie_secure,
        same_site="lax",
    )

    @app.get("/health")
    def health(session: Session = Depends(get_session)) -> dict[str, object]:
        check_database(session)
        return {"ok": True, "database": "ok"}

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request, session: Session = Depends(get_session)):
        if AuthService(session).setup_required():
            return RedirectResponse("/setup", status_code=HTTP_303_SEE_OTHER)
        require_user(request, session)
        projects = ProjectService(session).list_projects()
        return templates.TemplateResponse(request, "projects.html", {"request": request, "projects": projects})

    @app.get("/setup", response_class=HTMLResponse)
    def setup_form(request: Request, session: Session = Depends(get_session)):
        if not AuthService(session).setup_required():
            return RedirectResponse("/login", status_code=HTTP_303_SEE_OTHER)
        return templates.TemplateResponse(request, "setup.html", {"request": request, "error": None})

    @app.post("/setup", response_class=HTMLResponse)
    def setup_post(
        request: Request,
        username: str = Form(...),
        password: str = Form(...),
        session: Session = Depends(get_session),
    ):
        try:
            AuthService(session).setup_admin(username, hash_password(password))
        except DomainError as exc:
            return templates.TemplateResponse(request, "setup.html", {"request": request, "error": str(exc)}, status_code=400)
        request.session["username"] = username
        return RedirectResponse("/", status_code=HTTP_303_SEE_OTHER)

    @app.get("/login", response_class=HTMLResponse)
    def login_form(request: Request):
        return templates.TemplateResponse(request, "login.html", {"request": request, "error": None})

    @app.post("/login", response_class=HTMLResponse)
    def login_post(
        request: Request,
        username: str = Form(...),
        password: str = Form(...),
        session: Session = Depends(get_session),
    ):
        if login_limited(username):
            return templates.TemplateResponse(
                request, "login.html", {"request": request, "error": "Too many attempts"}, status_code=429
            )
        user = AuthService(session).get_user(username)
        if user is None or not verify_password(password, user.password_hash):
            note_failed_login(username)
            return templates.TemplateResponse(
                request, "login.html", {"request": request, "error": "Invalid login"}, status_code=400
            )
        clear_failed_login(username)
        request.session["username"] = user.username
        return RedirectResponse("/", status_code=HTTP_303_SEE_OTHER)

    @app.post("/logout")
    def logout(request: Request):
        request.session.clear()
        return RedirectResponse("/login", status_code=HTTP_303_SEE_OTHER)

    @app.post("/projects")
    def create_project(
        request: Request,
        name: str = Form(...),
        repo_url: str = Form(""),
        session: Session = Depends(get_session),
    ):
        require_user(request, session)
        try:
            project = ProjectService(session).create_project(name=name, repo_url=repo_url)
        except DomainError:
            return RedirectResponse("/", status_code=HTTP_303_SEE_OTHER)
        return RedirectResponse(f"/projects/{project.id}", status_code=HTTP_303_SEE_OTHER)

    @app.get("/projects/{project_id}", response_class=HTMLResponse)
    def project_detail(request: Request, project_id: int, session: Session = Depends(get_session)):
        require_user(request, session)
        project = ProjectService(session).get_project(project_id)
        issues = IssueService(session).search(project_id=project_id, limit=50)
        categories = CategoryService(session).list_categories(project_id)
        logs = IssueLogService(session).list_entries(project_id)
        return templates.TemplateResponse(
            request,
            "project_detail.html",
            {
                "request": request,
                "project": project,
                "issues": issues,
                "categories": categories,
                "logs": logs,
                "error": None,
            },
        )

    @app.post("/projects/{project_id}/categories")
    def create_category(
        request: Request,
        project_id: int,
        key: str = Form(...),
        name: str = Form(...),
        checklist: str = Form(...),
        session: Session = Depends(get_session),
    ):
        require_user(request, session)
        CategoryService(session).create_category(project_id, key, name, checklist)
        return RedirectResponse(f"/projects/{project_id}", status_code=HTTP_303_SEE_OTHER)

    @app.post("/projects/{project_id}/issues", response_class=HTMLResponse)
    def create_issue(
        request: Request,
        project_id: int,
        title: str = Form(...),
        acceptance_criteria: str = Form(""),
        category_id: int | None = Form(None),
        session: Session = Depends(get_session),
    ):
        require_user(request, session)
        try:
            IssueService(session).create_issue(project_id, title, acceptance_criteria, category_id=category_id)
        except DomainError as exc:
            project = ProjectService(session).get_project(project_id)
            issues = IssueService(session).search(project_id=project_id, limit=50)
            categories = CategoryService(session).list_categories(project_id)
            logs = IssueLogService(session).list_entries(project_id)
            return templates.TemplateResponse(
                request,
                "project_detail.html",
                {
                    "request": request,
                    "project": project,
                    "issues": issues,
                    "categories": categories,
                    "logs": logs,
                    "error": str(exc),
                },
                status_code=400,
            )
        return RedirectResponse(f"/projects/{project_id}", status_code=HTTP_303_SEE_OTHER)

    @app.get("/issues/{issue_id}", response_class=HTMLResponse)
    def issue_detail(request: Request, issue_id: int, session: Session = Depends(get_session)):
        require_user(request, session)
        issue = IssueService(session).get_issue(issue_id)
        dependencies = Repository(session).list_dependencies_for_issue(issue_id)
        return templates.TemplateResponse(
            request, "issue_detail.html", {"request": request, "issue": issue, "dependencies": dependencies}
        )

    @app.post("/issues/{issue_id}/close")
    def close_issue(
        request: Request,
        issue_id: int,
        originating_llm: str = Form(...),
        close_note: str = Form(""),
        session: Session = Depends(get_session),
    ):
        username = require_user(request, session)
        issue = IssueService(session).update_status(
            issue_id, "done", originating_llm=originating_llm, close_note=close_note, actor=username
        )
        return RedirectResponse(f"/projects/{issue.project_id}", status_code=HTTP_303_SEE_OTHER)

    @app.post("/issues/{blocked_issue_id}/dependencies")
    def add_dependency(
        request: Request,
        blocked_issue_id: int,
        blocker_issue_id: int = Form(...),
        session: Session = Depends(get_session),
    ):
        require_user(request, session)
        issue = IssueService(session).get_issue(blocked_issue_id)
        IssueService(session).add_dependency(blocker_issue_id, blocked_issue_id)
        return RedirectResponse(f"/issues/{issue.id}", status_code=HTTP_303_SEE_OTHER)

    @app.post("/projects/{project_id}/sprints")
    def create_sprint(
        request: Request,
        project_id: int,
        goal: str = Form(...),
        session: Session = Depends(get_session),
    ):
        require_user(request, session)
        sprint = SprintService(session).create_sprint(project_id, goal)
        return RedirectResponse(f"/sprints/{sprint.id}", status_code=HTTP_303_SEE_OTHER)

    @app.get("/sprints/{sprint_id}", response_class=HTMLResponse)
    def sprint_detail(request: Request, sprint_id: int, session: Session = Depends(get_session)):
        require_user(request, session)
        sprint = SprintService(session).get_sprint(sprint_id)
        memberships = Repository(session).list_sprint_issues(sprint_id)
        backlog = IssueService(session).search(project_id=sprint.project_id, status="backlog", limit=50)
        return templates.TemplateResponse(
            request,
            "sprint_detail.html",
            {"request": request, "sprint": sprint, "memberships": memberships, "backlog": backlog},
        )

    @app.post("/sprints/{sprint_id}/issues")
    def add_sprint_issue(
        request: Request,
        sprint_id: int,
        issue_id: int = Form(...),
        session: Session = Depends(get_session),
    ):
        require_user(request, session)
        SprintService(session).add_issue(sprint_id, issue_id)
        return RedirectResponse(f"/sprints/{sprint_id}", status_code=HTTP_303_SEE_OTHER)

    @app.post("/sprints/{sprint_id}/close")
    def close_sprint(request: Request, sprint_id: int, session: Session = Depends(get_session)):
        require_user(request, session)
        sprint = SprintService(session).close_sprint(sprint_id)
        return RedirectResponse(f"/projects/{sprint.project_id}", status_code=HTTP_303_SEE_OTHER)

    @app.exception_handler(KeyError)
    def not_found(_: Request, exc: KeyError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return app


app = create_app()
