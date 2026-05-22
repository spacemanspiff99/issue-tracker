from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware
from starlette.status import HTTP_303_SEE_OTHER

from issue_tracker.config import get_settings
from issue_tracker.db import check_database, get_session
from issue_tracker.repositories.store import Repository
from issue_tracker.services.backup_targets import VibecodingBackupService
from issue_tracker.services.guidance_sync import GuidanceSyncService
from issue_tracker.services.recovery_bundle import RecoveryBundleService
from issue_tracker.services.rule_relevance import RuleRelevanceService
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

VOICE_UPLOAD_ROOT = Path("exports/voice-feedback")


def project_detail_response(
    request: Request,
    session: Session,
    project_id: int,
    error: str | None = None,
    status_code: int = 200,
    view: str = "all",
    query: str = "",
):
    project = ProjectService(session).get_project(project_id)
    issue_service = IssueService(session)
    issues = issue_service.list_project_view(project_id, view=view, query=query)
    categories = CategoryService(session).list_categories(project_id)
    logs = IssueLogService(session).list_entries(project_id)
    repo = Repository(session)
    sprints = repo.list_project_sprints(project_id)
    summary = issue_service.project_summary(project_id)
    sprint_rollups = issue_service.sprint_rollups(project_id)
    release_rollups = issue_service.release_rollups(project_id)
    workflow_summary = issue_service.workflow_summary(project_id)
    overview_dashboard = issue_service.overview_dashboard(project_id)
    activity = issue_service.activity_feed(project_id, limit=20)
    dependency_health = {issue.id: issue_service.dependency_health(issue.id) for issue in issues}
    return templates.TemplateResponse(
        request,
        "project_detail.html",
        {
            "request": request,
            "project": project,
            "issues": issues,
            "categories": categories,
            "sprints": sprints,
            "logs": logs,
            "summary": summary,
            "sprint_rollups": sprint_rollups,
            "release_rollups": release_rollups,
            "workflow_summary": workflow_summary,
            "overview_dashboard": overview_dashboard,
            "activity": activity,
            "dependency_health": dependency_health,
            "view": view,
            "query": query,
            "saved_views": ["all", "backlog", "active-sprint", "blocked", "done", "uncategorized"],
            "error": error,
        },
        status_code=status_code,
    )


def issue_detail_context(session: Session, issue_id: int, error: str | None = None) -> dict[str, object]:
    issue_service = IssueService(session)
    issue = issue_service.get_issue(issue_id)
    repo = Repository(session)
    issue_logs = [
        entry for entry in IssueLogService(session).list_entries(issue.project_id) if entry.issue_id == issue_id
    ]
    return {
        "issue": issue,
        "project": ProjectService(session).get_project(issue.project_id),
        "dependencies": repo.list_dependencies_for_issue(issue_id),
        "categories": CategoryService(session).list_categories(issue.project_id),
        "sprints": repo.list_project_sprints(issue.project_id),
        "health": issue_service.dependency_health(issue_id),
        "workflow_state": issue_service.workflow_state(issue),
        "linked_prs": repo.list_linked_prs(issue_id),
        "events": [
            event for event in issue_service.activity_feed(issue.project_id) if event.issue_id == issue_id
        ],
        "issue_logs": issue_logs,
        "error": error,
    }


def safe_voice_upload_path(project_id: int, filename: str) -> Path:
    suffix = Path(filename).suffix.lower()
    if suffix not in {".webm", ".m4a", ".mp3", ".wav", ".ogg", ".flac"}:
        suffix = ".audio"
    return VOICE_UPLOAD_ROOT / str(project_id) / f"{uuid4().hex}{suffix}"


def sprint_detail_response(
    request: Request,
    session: Session,
    sprint_id: int,
    error: str | None = None,
    status_code: int = 200,
):
    sprint = SprintService(session).get_sprint(sprint_id)
    memberships = Repository(session).list_sprint_issues(sprint_id)
    backlog = IssueService(session).search(project_id=sprint.project_id, status="backlog", limit=50)
    rollup = next(
        item for item in IssueService(session).sprint_rollups(sprint.project_id) if item["sprint"].id == sprint.id
    )
    return templates.TemplateResponse(
        request,
        "sprint_detail.html",
        {
            "request": request,
            "sprint": sprint,
            "memberships": memberships,
            "backlog": backlog,
            "rollup": rollup,
            "error": error,
        },
        status_code=status_code,
    )


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
        return templates.TemplateResponse(
            request, "projects.html", {"request": request, "projects": projects, "query": "", "show_all": False}
        )

    @app.get("/search", response_class=HTMLResponse)
    def global_search(
        request: Request,
        q: str = "",
        show_all: bool = False,
        session: Session = Depends(get_session),
    ):
        require_user(request, session)
        projects = ProjectService(session).search_projects(q, include_inactive=show_all)
        return templates.TemplateResponse(
            request,
            "projects.html",
            {"request": request, "projects": projects, "query": q, "show_all": show_all},
        )

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
            return templates.TemplateResponse(
                request, "setup.html", {"request": request, "error": str(exc)}, status_code=400
            )
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
                request,
                "login.html",
                {"request": request, "error": "Too many attempts"},
                status_code=429,
            )
        user = AuthService(session).get_user(username)
        if user is None or not verify_password(password, user.password_hash):
            note_failed_login(username)
            return templates.TemplateResponse(
                request,
                "login.html",
                {"request": request, "error": "Invalid login"},
                status_code=400,
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

    @app.post("/projects/{project_id}/active")
    def set_project_active(
        request: Request,
        project_id: int,
        active: bool = Form(...),
        session: Session = Depends(get_session),
    ):
        require_user(request, session)
        ProjectService(session).set_project_active(project_id, active)
        return RedirectResponse("/search?show_all=true", status_code=HTTP_303_SEE_OTHER)

    @app.get("/projects/{project_id}", response_class=HTMLResponse)
    def project_detail(
        request: Request,
        project_id: int,
        view: str = "all",
        q: str = "",
        session: Session = Depends(get_session),
    ):
        require_user(request, session)
        return project_detail_response(request, session, project_id, view=view, query=q)

    @app.get("/projects/{project_id}/backlog", response_class=HTMLResponse)
    def backlog_view(
        request: Request,
        project_id: int,
        q: str = "",
        session: Session = Depends(get_session),
    ):
        require_user(request, session)
        project = ProjectService(session).get_project(project_id)
        issue_service = IssueService(session)
        issues = issue_service.list_project_view(project_id, view="backlog", query=q)
        repo = Repository(session)
        return templates.TemplateResponse(
            request,
            "backlog.html",
            {
                "request": request,
                "project": project,
                "issues": issues,
                "categories": CategoryService(session).list_categories(project_id),
                "sprints": repo.list_project_sprints(project_id),
                "dependency_health": {issue.id: issue_service.dependency_health(issue.id) for issue in issues},
                "query": q,
                "saved_views": ["all", "backlog", "active-sprint", "blocked", "done", "uncategorized"],
            },
        )

    @app.get("/projects/{project_id}/board", response_class=HTMLResponse)
    def board_view(
        request: Request,
        project_id: int,
        sprint_id: list[int] = Query(default=[]),
        all_sprints: bool = False,
        session: Session = Depends(get_session),
    ):
        require_user(request, session)
        project = ProjectService(session).get_project(project_id)
        repo = Repository(session)
        service = IssueService(session)
        sprints = repo.list_project_sprints(project_id)
        selected_sprint_ids = sprint_id
        if not selected_sprint_ids and not all_sprints:
            active = repo.active_sprint(project_id)
            selected_sprint_ids = [active.id] if active else []
        selected_issue_ids: set[int] | None = None
        if selected_sprint_ids:
            selected_issue_ids = {
                membership.issue_id
                for selected_id in selected_sprint_ids
                for membership in repo.list_sprint_issues(selected_id)
            }
        issues = service.list_project_view(project_id, view="all", query="")
        if selected_issue_ids is not None:
            issues = [issue for issue in issues if issue.id in selected_issue_ids]
        columns = {
            "backlog": [issue for issue in issues if issue.status.value == "backlog"],
            "in-progress": [issue for issue in issues if issue.status.value == "in-progress"],
            "done": [issue for issue in issues if issue.status.value == "done"],
        }
        backlog = service.list_project_view(project_id, view="backlog")
        return templates.TemplateResponse(
            request,
            "board.html",
            {
                "request": request,
                "project": project,
                "columns": columns,
                "sprints": sprints,
                "selected_sprint_ids": selected_sprint_ids,
                "all_sprints": all_sprints,
                "backlog": backlog,
            },
        )

    @app.get("/projects/{project_id}/releases", response_class=HTMLResponse)
    def release_view(request: Request, project_id: int, session: Session = Depends(get_session)):
        require_user(request, session)
        project = ProjectService(session).get_project(project_id)
        return templates.TemplateResponse(
            request,
            "releases.html",
            {
                "request": request,
                "project": project,
                "release_rollups": IssueService(session).release_rollups(project_id),
            },
        )

    @app.get("/projects/{project_id}/intake", response_class=HTMLResponse)
    def intake_view(request: Request, project_id: int, session: Session = Depends(get_session)):
        require_user(request, session)
        project = ProjectService(session).get_project(project_id)
        workflow_summary = IssueService(session).workflow_summary(project_id)
        intakes = [
            issue
            for issue in IssueService(session).list_project_view(project_id, view="all")
            if IssueService(session).workflow_state(issue) in {"intake", "clarify", "ready-for-codex"}
        ]
        return templates.TemplateResponse(
            request,
            "intake.html",
            {
                "request": request,
                "project": project,
                "workflow_summary": workflow_summary,
                "intakes": intakes,
                "error": None,
            },
        )

    @app.get("/projects/{project_id}/backup", response_class=HTMLResponse)
    def backup_view(request: Request, project_id: int, session: Session = Depends(get_session)):
        require_user(request, session)
        project = ProjectService(session).get_project(project_id)
        health = RecoveryBundleService(session).backup_health(project_id)
        vibecoding_plan = VibecodingBackupService(session).plan_target_paths(project_id)
        return templates.TemplateResponse(
            request,
            "backup.html",
            {"request": request, "project": project, "backup_health": health, "vibecoding_plan": vibecoding_plan},
        )

    @app.get("/projects/{project_id}/planning", response_class=HTMLResponse)
    def planning_view(request: Request, project_id: int, session: Session = Depends(get_session)):
        require_user(request, session)
        project = ProjectService(session).get_project(project_id)
        return templates.TemplateResponse(request, "planning.html", {"request": request, "project": project})

    @app.get("/projects/{project_id}/guidance-sync", response_class=HTMLResponse)
    def guidance_sync_view(request: Request, project_id: int, session: Session = Depends(get_session)):
        require_user(request, session)
        project = ProjectService(session).get_project(project_id)
        dashboard = GuidanceSyncService(session).dashboard(project_id)
        rule_health = RuleRelevanceService().sync_next_actions(["fastapi-jinja-postgres", "mcp-server", "dogfood"])
        return templates.TemplateResponse(
            request,
            "guidance_sync.html",
            {"request": request, "project": project, "dashboard": dashboard, "rule_health": rule_health},
        )

    @app.get("/projects/{project_id}/categories", response_class=HTMLResponse)
    def categories_view(request: Request, project_id: int, session: Session = Depends(get_session)):
        require_user(request, session)
        project = ProjectService(session).get_project(project_id)
        issues = IssueService(session).list_project_view(project_id)
        categories = CategoryService(session).list_categories(project_id)
        issue_counts = {
            category.id: sum(1 for issue in issues if issue.category_id == category.id) for category in categories
        }
        uncategorized_count = sum(1 for issue in issues if issue.category_id is None)
        return templates.TemplateResponse(
            request,
            "categories.html",
            {
                "request": request,
                "project": project,
                "categories": categories,
                "issue_counts": issue_counts,
                "uncategorized_count": uncategorized_count,
            },
        )

    @app.get("/projects/{project_id}/sprints", response_class=HTMLResponse)
    def sprints_view(request: Request, project_id: int, session: Session = Depends(get_session)):
        require_user(request, session)
        project = ProjectService(session).get_project(project_id)
        issue_service = IssueService(session)
        repo = Repository(session)
        return templates.TemplateResponse(
            request,
            "sprints.html",
            {
                "request": request,
                "project": project,
                "sprints": repo.list_project_sprints(project_id),
                "rollups": issue_service.sprint_rollups(project_id),
                "backlog": issue_service.list_project_view(project_id, view="backlog"),
            },
        )

    @app.post("/projects/{project_id}/categories")
    def create_category(
        request: Request,
        project_id: int,
        key: str = Form(""),
        name: str = Form(""),
        checklist: str = Form(""),
        session: Session = Depends(get_session),
    ):
        require_user(request, session)
        try:
            CategoryService(session).create_category(project_id, key, name, checklist)
        except DomainError as exc:
            return project_detail_response(request, session, project_id, error=str(exc), status_code=400)
        return RedirectResponse(f"/projects/{project_id}", status_code=HTTP_303_SEE_OTHER)

    @app.post("/projects/{project_id}/categories/base")
    def create_base_taxonomy(request: Request, project_id: int, session: Session = Depends(get_session)):
        require_user(request, session)
        CategoryService(session).ensure_base_taxonomy(project_id)
        return RedirectResponse(f"/projects/{project_id}", status_code=HTTP_303_SEE_OTHER)

    @app.post("/projects/{project_id}/issues", response_class=HTMLResponse)
    def create_issue(
        request: Request,
        project_id: int,
        title: str = Form(""),
        acceptance_criteria: str = Form(""),
        priority: str = Form("normal"),
        category_id: int | None = Form(None),
        session: Session = Depends(get_session),
    ):
        require_user(request, session)
        try:
            service = IssueService(session)
            if category_id is None:
                recommended = service.category_recommendation(project_id, title, acceptance_criteria)
                category_id = recommended.id if recommended else None
            service.create_issue(
                project_id,
                title,
                acceptance_criteria,
                priority=priority,
                category_id=category_id,
            )
        except DomainError as exc:
            return project_detail_response(request, session, project_id, error=str(exc), status_code=400)
        return RedirectResponse(f"/projects/{project_id}", status_code=HTTP_303_SEE_OTHER)

    @app.get("/issues/{issue_id}", response_class=HTMLResponse)
    def issue_detail(request: Request, issue_id: int, session: Session = Depends(get_session)):
        require_user(request, session)
        context = issue_detail_context(session, issue_id)
        context["request"] = request
        return templates.TemplateResponse(request, "issue_detail.html", context)

    @app.post("/issues/{issue_id}/edit")
    def edit_issue(
        request: Request,
        issue_id: int,
        title: str = Form(""),
        acceptance_criteria: str = Form(""),
        priority: str = Form("normal"),
        summary: str = Form(""),
        proposed_approach: str = Form(""),
        category_id: int | None = Form(None),
        status: str = Form(""),
        session: Session = Depends(get_session),
    ):
        username = require_user(request, session)
        issue = IssueService(session).get_issue(issue_id)
        try:
            IssueService(session).update_issue(
                issue_id,
                title=title,
                acceptance_criteria=acceptance_criteria,
                priority=priority,
                summary=summary,
                proposed_approach=proposed_approach,
                category_id=category_id,
                status=status or None,
                actor=username,
            )
        except DomainError as exc:
            return project_detail_response(request, session, issue.project_id, error=str(exc), status_code=400)
        return RedirectResponse(f"/issues/{issue_id}", status_code=HTTP_303_SEE_OTHER)

    @app.post("/issues/{issue_id}/metadata")
    def edit_issue_metadata(
        request: Request,
        issue_id: int,
        labels: str = Form(""),
        story: str = Form(""),
        delivery_phase: str = Form(""),
        milestone: str = Form(""),
        custom_fields: str = Form(""),
        session: Session = Depends(get_session),
    ):
        username = require_user(request, session)
        IssueService(session).update_planning_metadata(
            issue_id,
            labels=labels,
            story=story,
            delivery_phase=delivery_phase,
            milestone=milestone,
            custom_fields=custom_fields,
            actor=username,
        )
        return RedirectResponse(f"/issues/{issue_id}", status_code=HTTP_303_SEE_OTHER)

    @app.post("/issues/{issue_id}/workflow")
    def edit_issue_workflow(
        request: Request,
        issue_id: int,
        workflow_state: str = Form(""),
        session: Session = Depends(get_session),
    ):
        username = require_user(request, session)
        try:
            IssueService(session).update_workflow_state(issue_id, workflow_state, actor=username)
        except DomainError as exc:
            context = issue_detail_context(session, issue_id, error=str(exc))
            context["request"] = request
            return templates.TemplateResponse(request, "issue_detail.html", context, status_code=400)
        return RedirectResponse(f"/issues/{issue_id}", status_code=HTTP_303_SEE_OTHER)

    @app.post("/issues/{issue_id}/sprints")
    def assign_issue_to_sprint(
        request: Request,
        issue_id: int,
        sprint_id: int = Form(...),
        session: Session = Depends(get_session),
    ):
        require_user(request, session)
        try:
            SprintService(session).add_issue(sprint_id, issue_id)
        except DomainError as exc:
            context = issue_detail_context(session, issue_id, error=str(exc))
            context["request"] = request
            return templates.TemplateResponse(request, "issue_detail.html", context, status_code=400)
        return RedirectResponse(f"/issues/{issue_id}", status_code=HTTP_303_SEE_OTHER)

    @app.post("/issues/{issue_id}/comments")
    def add_issue_comment(
        request: Request,
        issue_id: int,
        message: str = Form(""),
        session: Session = Depends(get_session),
    ):
        username = require_user(request, session)
        IssueService(session).add_comment(issue_id, message, actor=username)
        return RedirectResponse(f"/issues/{issue_id}", status_code=HTTP_303_SEE_OTHER)

    @app.post("/issues/{issue_id}/references")
    def add_issue_reference(
        request: Request,
        issue_id: int,
        repo: str = Form(""),
        url: str = Form(""),
        pr_number: int | None = Form(None),
        merge_status: str = Form(""),
        session: Session = Depends(get_session),
    ):
        username = require_user(request, session)
        IssueService(session).add_linked_reference(
            issue_id, repo=repo, url=url, pr_number=pr_number, merge_status=merge_status, actor=username
        )
        return RedirectResponse(f"/issues/{issue_id}", status_code=HTTP_303_SEE_OTHER)

    @app.post("/issues/{issue_id}/status")
    def inline_status(
        request: Request,
        issue_id: int,
        status: str = Form(...),
        priority: str = Form(""),
        session: Session = Depends(get_session),
    ):
        username = require_user(request, session)
        issue = IssueService(session).get_issue(issue_id)
        IssueService(session).update_issue(
            issue_id,
            status=status,
            priority=priority or issue.priority,
            actor=username,
        )
        return RedirectResponse(f"/projects/{issue.project_id}", status_code=HTTP_303_SEE_OTHER)

    @app.post("/projects/{project_id}/backlog/reorder")
    def reorder_backlog(
        request: Request,
        project_id: int,
        ordered_issue_ids: str = Form(""),
        session: Session = Depends(get_session),
    ):
        require_user(request, session)
        issue_ids = [int(value) for value in ordered_issue_ids.split(",") if value.strip().isdigit()]
        IssueService(session).reorder_backlog(project_id, issue_ids)
        return RedirectResponse(f"/projects/{project_id}/backlog", status_code=HTTP_303_SEE_OTHER)

    @app.post("/projects/{project_id}/voice-feedback")
    async def create_voice_feedback(
        request: Request,
        project_id: int,
        title: str = Form(""),
        notes: str = Form(""),
        priority: str = Form("normal"),
        ambiguous: bool = Form(False),
        autosave: bool = Form(False),
        replace_issue_id: int | None = Form(None),
        audio: UploadFile | None = File(None),
        session: Session = Depends(get_session),
    ):
        username = require_user(request, session)
        issue_service = IssueService(session)
        if autosave and (audio is None or not audio.filename):
            return JSONResponse({"ok": False, "error": "Audio recording is required for autosave"}, status_code=400)
        stored_path = None
        if audio and audio.filename:
            stored_path = safe_voice_upload_path(project_id, audio.filename)
            stored_path.parent.mkdir(parents=True, exist_ok=True)
            total = 0
            with stored_path.open("wb") as output:
                while chunk := await audio.read(1024 * 1024):
                    total += len(chunk)
                    if total > 25 * 1024 * 1024:
                        output.close()
                        stored_path.unlink(missing_ok=True)
                        if autosave:
                            return JSONResponse(
                                {"ok": False, "error": "Audio upload is limited to 25 MB"},
                                status_code=400,
                            )
                        project = ProjectService(session).get_project(project_id)
                        return templates.TemplateResponse(
                            request,
                            "intake.html",
                            {
                                "request": request,
                                "project": project,
                                "workflow_summary": IssueService(session).workflow_summary(project_id),
                                "intakes": IssueService(session).list_project_view(project_id, view="all"),
                                "error": "Audio upload is limited to 25 MB",
                            },
                            status_code=400,
                        )
                    output.write(chunk)
        if replace_issue_id is not None:
            try:
                issue_service.delete_voice_intake(replace_issue_id, actor=username)
            except DomainError as exc:
                if stored_path is not None:
                    stored_path.unlink(missing_ok=True)
                if autosave:
                    return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
                raise
        issue = issue_service.create_voice_intake(
            project_id,
            title,
            notes,
            stored_path,
            ambiguous,
            priority=priority,
            actor=username,
        )
        if autosave:
            return JSONResponse(
                {
                    "ok": True,
                    "issue_id": issue.id,
                    "issue_sequence": display_id(issue.sequence),
                    "title": issue.title,
                    "summary": issue.summary,
                    "url": f"/issues/{issue.id}",
                }
            )
        return RedirectResponse(f"/projects/{project_id}/intake", status_code=HTTP_303_SEE_OTHER)

    @app.post("/issues/{issue_id}/voice-intake/delete")
    def delete_voice_intake(request: Request, issue_id: int, session: Session = Depends(get_session)):
        username = require_user(request, session)
        try:
            IssueService(session).delete_voice_intake(issue_id, actor=username)
        except DomainError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
        return JSONResponse({"ok": True})

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
        try:
            IssueService(session).add_dependency(blocker_issue_id, blocked_issue_id)
        except DomainError as exc:
            dependencies = Repository(session).list_dependencies_for_issue(blocked_issue_id)
            return templates.TemplateResponse(
                request,
                "issue_detail.html",
                {
                    "request": request,
                    "issue": issue,
                    "dependencies": dependencies,
                    "categories": CategoryService(session).list_categories(issue.project_id),
                    "health": IssueService(session).dependency_health(blocked_issue_id),
                    "linked_prs": Repository(session).list_linked_prs(blocked_issue_id),
                    "events": [
                        event
                        for event in IssueService(session).activity_feed(issue.project_id)
                        if event.issue_id == blocked_issue_id
                    ],
                    "error": str(exc),
                },
                status_code=400,
            )
        return RedirectResponse(f"/issues/{issue.id}", status_code=HTTP_303_SEE_OTHER)

    @app.post("/projects/{project_id}/sprints")
    def create_sprint(
        request: Request,
        project_id: int,
        goal: str = Form(""),
        context: str = Form(""),
        session: Session = Depends(get_session),
    ):
        require_user(request, session)
        try:
            sprint = SprintService(session).create_sprint(project_id, goal, context=context)
        except DomainError as exc:
            return project_detail_response(request, session, project_id, error=str(exc), status_code=400)
        return RedirectResponse(f"/sprints/{sprint.id}", status_code=HTTP_303_SEE_OTHER)

    @app.get("/sprints/{sprint_id}", response_class=HTMLResponse)
    def sprint_detail(request: Request, sprint_id: int, session: Session = Depends(get_session)):
        require_user(request, session)
        return sprint_detail_response(request, session, sprint_id)

    @app.post("/sprints/{sprint_id}/issues")
    def add_sprint_issue(
        request: Request,
        sprint_id: int,
        issue_id: int = Form(...),
        session: Session = Depends(get_session),
    ):
        require_user(request, session)
        try:
            SprintService(session).add_issue(sprint_id, issue_id)
        except DomainError as exc:
            return sprint_detail_response(request, session, sprint_id, error=str(exc), status_code=400)
        return RedirectResponse(f"/sprints/{sprint_id}", status_code=HTTP_303_SEE_OTHER)

    @app.post("/sprints/{sprint_id}/issues/reorder")
    def reorder_sprint_issues(
        request: Request,
        sprint_id: int,
        ordered_issue_ids: str = Form(""),
        session: Session = Depends(get_session),
    ):
        require_user(request, session)
        sprint = SprintService(session).get_sprint(sprint_id)
        issue_ids = [int(value) for value in ordered_issue_ids.split(",") if value.strip().isdigit()]
        memberships = Repository(session).list_sprint_issues(sprint_id)
        ranks = {issue_id: index + 1 for index, issue_id in enumerate(issue_ids)}
        for membership in memberships:
            if membership.issue_id in ranks:
                membership.sort_order = ranks[membership.issue_id]
        session.commit()
        return RedirectResponse(
            f"/projects/{sprint.project_id}/board?sprint_id={sprint_id}",
            status_code=HTTP_303_SEE_OTHER,
        )

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
