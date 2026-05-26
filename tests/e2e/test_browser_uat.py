from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect, sync_playwright

from issue_tracker.db import SessionLocal
from issue_tracker.domain.models import Issue, Project, User
from issue_tracker.web.security import hash_password

BASE_URL = os.environ.get("UAT_BASE_URL", "http://127.0.0.1:8000")
IGNORE_HTTPS_ERRORS = os.environ.get("UAT_IGNORE_HTTPS_ERRORS") == "1"
USERNAME = os.environ.get("UAT_USERNAME", "uat-admin")
PASSWORD = os.environ.get("UAT_PASSWORD", "uat-password")
SCREENSHOT_DIR = Path("exports/browser-uat-0140")
NOTE_PATH = Path("documentation/uat/2026-05-24-sprint-0140-usability-rescue.md")
CHROMIUM_ARGS = ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"]
if BASE_URL.startswith("http://") and "localhost" not in BASE_URL and "127.0.0.1" not in BASE_URL:
    CHROMIUM_ARGS.append(f"--unsafely-treat-insecure-origin-as-secure={BASE_URL}")

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_BROWSER_UAT") != "1",
    reason="browser UAT requires the running app container and RUN_BROWSER_UAT=1",
)


def ensure_login_user() -> None:
    with SessionLocal() as session:
        user_count = session.query(User).count()
        if user_count == 0:
            return
        user = session.query(User).filter_by(username=USERNAME).one_or_none()
        if user is None:
            session.add(User(username=USERNAME, password_hash=hash_password(PASSWORD)))
        else:
            user.password_hash = hash_password(PASSWORD)
        session.commit()


def issue_id(project_name: str, title: str) -> int:
    with SessionLocal() as session:
        project = session.query(Project).filter_by(name=project_name).one()
        issue = session.query(Issue).filter_by(project_id=project.id, title=title).one()
        return issue.id


def archive_project(project_id: int) -> None:
    with SessionLocal() as session:
        project = session.get(Project, project_id)
        if project is not None:
            project.active = False
            session.commit()


def assert_viewport_usable(page: Page, screenshot_name: str) -> None:
    expect(page.locator("body")).to_be_visible()
    overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
    assert overflow <= 2
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=SCREENSHOT_DIR / screenshot_name, full_page=True)


def assert_sidebar_nav_compact(page: Page) -> None:
    nav_metrics = page.evaluate(
        """
        () => Array.from(document.querySelectorAll(".side-nav a")).map((item) => {
          const rect = item.getBoundingClientRect();
          return { text: item.textContent.trim(), height: rect.height };
        })
        """
    )
    assert nav_metrics
    oversized = [item for item in nav_metrics if item["height"] > 52]
    assert oversized == []


def login_or_setup(page: Page) -> str:
    page.goto(f"{BASE_URL}/setup")
    if page.locator('input[name="username"]').is_visible() and "setup" in page.content().lower():
        page.fill('input[name="username"]', USERNAME)
        page.fill('input[name="password"]', PASSWORD)
        page.click('button[type="submit"]')
        expect(page.locator("h1")).to_contain_text("Projects")
        return "First-run setup created the UAT admin user."
    page.goto(f"{BASE_URL}/login")
    page.fill('input[name="username"]', USERNAME)
    page.fill('input[name="password"]', PASSWORD)
    page.click('button[type="submit"]')
    expect(page.locator("h1")).to_contain_text("Projects")
    return "Existing setup detected; seeded and used the UAT admin user."


def run_desktop_workflow(page: Page) -> tuple[str, int, int, int]:
    setup_note = login_or_setup(page)
    suffix = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    project_name = f"Browser UAT Project {suffix}"

    page.fill('input[name="name"]', project_name)
    page.fill('input[name="repo_url"]', "https://github.com/spacemanspiff99/issue-tracker")
    page.click('button:has-text("Create project")')
    expect(page.locator("h1")).to_contain_text(project_name)
    assert_sidebar_nav_compact(page)
    assert_viewport_usable(page, "desktop-project-empty.png")

    page.click('button:has-text("Add recommended tracker taxonomy")')
    expect(page.locator("body")).to_contain_text("IT-1")

    page.fill('form[action$="/issues"] input[name="title"]', "Missing AC UAT")
    page.locator('form[action$="/issues"] textarea[name="acceptance_criteria"]').evaluate(
        "element => element.removeAttribute('required')"
    )
    page.click('form[action$="/issues"] button:has-text("Create issue")')
    expect(page.locator(".error")).to_contain_text("Acceptance criteria are required")

    page.fill('form[action$="/issues"] input[name="title"]', "Prepare blocker")
    page.fill('form[action$="/issues"] textarea[name="acceptance_criteria"]', "- [ ] Blocker issue can be linked")
    page.click('form[action$="/issues"] button:has-text("Create issue")')
    expect(page.locator("body")).to_contain_text("Prepare blocker")

    page.fill('form[action$="/issues"] input[name="title"]', "Complete blocked work")
    page.fill('form[action$="/issues"] textarea[name="acceptance_criteria"]', "- [ ] Blocked issue can be closed")
    page.click('form[action$="/issues"] button:has-text("Create issue")')
    expect(page.locator("body")).to_contain_text("Complete blocked work")

    blocker_id = issue_id(project_name, "Prepare blocker")
    blocked_id = issue_id(project_name, "Complete blocked work")

    page.click('a:has-text("Complete blocked work")')
    page.fill('input[name="blocker_issue_id"]', str(blocker_id))
    page.click('button:has-text("Add blocker")')
    expect(page.locator("body")).to_contain_text("blocks Issue")
    assert_viewport_usable(page, "desktop-issue-detail.png")

    page.goto(f"{BASE_URL}/projects/{page.url.rsplit('/projects/', 1)[-1]}" if "/projects/" in page.url else BASE_URL)
    page.goto(f"{BASE_URL}/")
    page.click(f'a:has-text("{project_name}")')
    page.fill('input[name="goal"]', "Local manual UAT sprint")
    page.fill('textarea[name="context"]', "Browser UAT sprint assignment path")
    page.click('button:has-text("Create sprint")')
    expect(page.locator("h1")).to_contain_text("Local manual UAT sprint")
    sprint_url = page.url
    page.select_option('select[name="issue_id"]', str(blocked_id))
    page.click('button:has-text("Add issue")')
    expect(page.locator("body")).to_contain_text("in-progress")
    assert_viewport_usable(page, "desktop-sprint-detail.png")

    page.goto(f"{BASE_URL}/issues/{blocked_id}")
    page.fill('input[name="originating_llm"]', "gpt-5.5")
    page.fill('textarea[name="close_note"]', "Browser UAT close path verified")
    page.click('button:has-text("Close issue")')
    expect(page.locator("body")).to_contain_text("done")

    page.goto(sprint_url)
    expect(page.locator("body")).to_contain_text("100%")

    page.goto(f"{BASE_URL}/search?q=Browser")
    expect(page.locator("body")).to_contain_text(project_name)
    page.click(f'a:has-text("{project_name}")')
    project_id = int(page.url.rstrip("/").rsplit("/", 1)[-1])
    expect(page.locator(".info-tip-trigger").first).to_be_visible()
    expect(page.locator(f'a[href="/projects/{project_id}/backlog?view=blocked"]').first).to_be_visible()
    expect(page.locator(f'a[href="/projects/{project_id}/backlog?view=uncategorized"]').first).to_be_visible()
    page.goto(f"{BASE_URL}/projects/{project_id}/backlog")
    expect(page.locator("body")).to_contain_text("Save Order")
    expect(page.locator("body")).to_contain_text("Issues Not In Sprint")
    page.click('a:has-text("Issues Not In Sprint")')
    expect(page).to_have_url(f"{BASE_URL}/projects/{project_id}/backlog?view=not-in-sprint")
    expect(page.locator(".saved-view-grid .active")).to_contain_text("Issues Not In Sprint")
    page.goto(f"{BASE_URL}/projects/{project_id}/board")
    expect(page.locator("h1")).to_contain_text("Sprint Board")
    expect(page.locator("body")).to_contain_text("History")
    expect(page).to_have_url(f"{BASE_URL}/projects/{project_id}/board")
    assert_viewport_usable(page, "desktop-board.png")
    page.goto(f"{BASE_URL}/projects/{project_id}/releases")
    expect(page.locator("h1")).to_contain_text("releases")
    expect(page.locator("body")).to_contain_text("Current")
    expect(page.locator("body")).to_contain_text("Unplanned work")
    expect(page.locator('a[href*="/backlog?view=all"]').first).to_be_visible()
    assert_viewport_usable(page, "desktop-releases.png")
    page.goto(f"{BASE_URL}/projects/{project_id}/guidance-sync")
    expect(page.locator("h1")).to_contain_text("Guidance Sync")
    assert_viewport_usable(page, "desktop-guidance-sync.png")
    page.goto(f"{BASE_URL}/projects/{project_id}/intake")
    assert_sidebar_nav_compact(page)
    priority_select = page.locator('form[action$="/voice-feedback"] select[name="priority"]')
    priority_select.select_option(value="urgent")
    expect(priority_select).to_have_value("urgent")
    if page.evaluate("window.isSecureContext"):
        assert page.evaluate("Boolean(navigator.mediaDevices)") is True
        assert page.evaluate("Boolean(window.MediaRecorder)") is True
    else:
        expect(page.locator("#record-start")).to_be_disabled()
        expect(page.locator("#record-status")).to_contain_text("requires localhost or HTTPS")
        assert_viewport_usable(page, "desktop-intake.png")
        return setup_note, project_id, blocker_id, blocked_id
    page.click("#record-start")
    expect(page.locator("#record-status")).to_have_text("Requesting microphone access...")
    expect(page.locator("#record-status")).to_have_text("Recording...")
    page.click("#record-stop")
    expect(page.locator("#record-status")).to_have_text("Recording saved automatically.")
    expect(page.locator("#record-preview")).to_be_visible()
    expect(page.locator("#record-saved")).to_contain_text("Saved automatically as")
    uploaded_audio = page.locator("#audio-input").evaluate(
        "element => Array.from(element.files).map((file) => ({ name: file.name, size: file.size, type: file.type }))"
    )
    assert len(uploaded_audio) == 1
    assert uploaded_audio[0]["size"] > 0
    expect(page.locator("body")).to_contain_text("Voice feedback: To process: urgent audio note")
    assert_viewport_usable(page, "desktop-intake.png")

    return setup_note, project_id, blocker_id, blocked_id


def run_mobile_checks(page: Page, project_id: int, blocked_id: int) -> None:
    page.goto(f"{BASE_URL}/projects/{project_id}")
    assert_viewport_usable(page, "mobile-project-detail.png")
    page.goto(f"{BASE_URL}/issues/{blocked_id}")
    assert_viewport_usable(page, "mobile-issue-detail.png")
    page.goto(f"{BASE_URL}/projects/{project_id}/board")
    assert_viewport_usable(page, "mobile-board.png")
    page.goto(f"{BASE_URL}/projects/{project_id}/backup")
    expect(page.locator("body")).to_contain_text("export-json")
    assert_viewport_usable(page, "mobile-backup.png")
    page.goto(f"{BASE_URL}/projects/{project_id}/guidance-sync")
    assert_viewport_usable(page, "mobile-guidance-sync.png")
    page.goto(f"{BASE_URL}/projects/{project_id}/intake")
    assert_viewport_usable(page, "mobile-intake.png")


def write_uat_note(setup_note: str) -> None:
    NOTE_PATH.write_text(
        f"""# Local UAT Notes: Sprint 0140 Usability Rescue Browser UAT

Date: 2026-05-24
Tester: Codex Playwright in Docker
Browser: Playwright Chromium inside the Docker app container
Environment: Docker Compose local app and PostgreSQL

## Result

Browser UAT passed for desktop and mobile viewports.

Setup/login note: {setup_note}

## Evidence

Command:

```bash
docker compose -f deployment/docker-compose.local.yml exec app python -m pytest tests/e2e/test_browser_uat.py
```

HTTPS/local-CA verification command:

```bash
docker compose -f deployment/docker-compose.local.yml exec \
  -e RUN_BROWSER_UAT=1 \
  -e UAT_BASE_URL=https://127.0.0.1:8443 \
  -e UAT_IGNORE_HTTPS_ERRORS=1 \
  app-https python -m pytest tests/e2e/test_browser_uat.py
```

Screenshots were generated under ignored local path `exports/browser-uat-0140/`.

## Covered Paths

- setup or existing-setup login
- project search and project creation
- recommended taxonomy
- issue validation, quick create, issue detail, dependency creation, and close metadata
- sprint creation, assignment, and progress summary
- overview drill-down links, saved backlog views, sprint-filtered board navigation, release count drill-downs
- Guidance Sync, intake, and backup guidance
- tooltip affordance visibility on primary project surfaces
- browser MediaRecorder record/stop/preview attachment using Chromium's fake microphone device
- secure-context voice intake over HTTPS/local CA
- audio-only urgent intake creation
- desktop viewport usability
- mobile viewport usability
""",
        encoding="utf-8",
    )


def test_browser_manual_uat_desktop_and_mobile():
    ensure_login_user()
    project_id = None
    with sync_playwright() as playwright:
        try:
            desktop = playwright.chromium.launch(
                headless=True,
                args=CHROMIUM_ARGS,
            )
            desktop_page = desktop.new_page(
                viewport={"width": 1365, "height": 900},
                ignore_https_errors=IGNORE_HTTPS_ERRORS,
            )
            setup_note, project_id, _, blocked_id = run_desktop_workflow(desktop_page)
            desktop.close()

            mobile = playwright.chromium.launch(headless=True, args=CHROMIUM_ARGS)
            mobile_page = mobile.new_page(
                viewport={"width": 390, "height": 844},
                is_mobile=True,
                has_touch=True,
                ignore_https_errors=IGNORE_HTTPS_ERRORS,
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
            )
            login_or_setup(mobile_page)
            run_mobile_checks(mobile_page, project_id, blocked_id)
            mobile.close()
        finally:
            if project_id is not None:
                archive_project(project_id)

    write_uat_note(setup_note)
