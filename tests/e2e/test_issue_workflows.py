"""W-ISSUE-CREATE, W-DEPENDENCY, W-SPRINT, W-ISSUE-CLOSE."""

from __future__ import annotations

import re

import pytest
from e2e_support import Step, create_issue, create_project, unique
from playwright.sync_api import Page, expect

BUG_0019 = "issue 0019: web routes turn DomainError into 500 / miss close validation and metadata"


def _issue_row(page: Page, title: str):
    return page.get_by_role("row").filter(has=page.get_by_role("link", name=title, exact=True))


def test_create_issue(user_page: Page, step: Step) -> None:
    page = user_page
    project_id = create_project(page, unique("E2E Issues"))
    title = unique("Create flow")
    expect(page.get_by_role("heading", name="Create issue")).to_be_visible()
    step("project-issue-form-visible")

    page.get_by_label("Title").fill(title)
    page.get_by_role("button", name="Create issue").click()
    criteria = page.get_by_label("Acceptance criteria")
    expect(page).to_have_url(re.compile(rf"/projects/{project_id}$"))
    assert criteria.evaluate("el => !el.validity.valid")
    expect(page.get_by_role("link", name=title, exact=True)).to_have_count(0)
    step("missing-ac-blocked-by-browser")

    criteria.fill("   ")
    page.get_by_role("button", name="Create issue").click()
    expect(page.locator(".error")).to_have_text("Acceptance criteria are required")
    expect(page.get_by_role("link", name=title, exact=True)).to_have_count(0)
    step("blank-ac-server-error")

    page.get_by_label("Title").fill(title)
    page.get_by_label("Acceptance criteria").fill("Given a project\nWhen I submit\nThen the issue exists")
    page.get_by_role("button", name="Create issue").click()
    row = _issue_row(page, title)
    expect(row).to_have_count(1)
    expect(row.get_by_role("cell").first).to_have_text("0001")
    expect(row).to_contain_text("backlog")
    step("issue-created-with-nnnn-id")

    row.get_by_role("link", name=title).click()
    expect(page.get_by_role("heading", name=f"Issue 0001: {title}")).to_be_visible()
    expect(page.locator("pre")).to_contain_text("Then the issue exists")
    step("issue-detail-shows-ac")


def test_dependency(user_page: Page, step: Step) -> None:
    page = user_page
    project_id = create_project(page, unique("E2E Deps"))
    blocker = create_issue(page, project_id, unique("Blocker"))
    blocked = create_issue(page, project_id, unique("Blocked"))
    edge = f"{blocker} blocks {blocked}"

    page.goto(f"/issues/{blocked}")
    page.get_by_label("Blocker issue ID").fill(str(blocker))
    step("blocker-form-filled")
    page.get_by_role("button", name="Add blocker").click()
    expect(page).to_have_url(re.compile(rf"/issues/{blocked}$"))
    expect(page.get_by_role("listitem").filter(has_text=edge)).to_have_count(1)
    step("dependency-shown-on-blocked")

    page.goto(f"/issues/{blocker}")
    expect(page.get_by_role("listitem").filter(has_text=edge)).to_have_count(1)
    step("dependency-shown-on-blocker")


@pytest.mark.xfail(strict=True, reason=BUG_0019)
def test_dependency_cycle_rejected(user_page: Page, step: Step) -> None:
    page = user_page
    project_id = create_project(page, unique("E2E Cycle"))
    blocker = create_issue(page, project_id, unique("Blocker"))
    blocked = create_issue(page, project_id, unique("Blocked"))
    page.goto(f"/issues/{blocked}")
    page.get_by_label("Blocker issue ID").fill(str(blocker))
    page.get_by_role("button", name="Add blocker").click()
    expect(page.get_by_role("listitem").filter(has_text=f"{blocker} blocks {blocked}")).to_have_count(1)
    step("forward-edge-added")

    page.goto(f"/issues/{blocker}")
    page.get_by_label("Blocker issue ID").fill(str(blocked))
    page.get_by_role("button", name="Add blocker").click()
    step("reverse-edge-submitted")
    expect(page.get_by_text("Dependency would create a cycle")).to_be_visible()
    expect(page.get_by_role("listitem").filter(has_text=f"{blocked} blocks {blocker}")).to_have_count(0)


def test_sprint(user_page: Page, step: Step) -> None:
    page = user_page
    project_id = create_project(page, unique("E2E Sprint"))
    title = unique("Sprint member")
    create_issue(page, project_id, title)
    goal = unique("Ship e2e")

    page.get_by_label("Goal").fill(goal)
    step("sprint-form-filled")
    page.get_by_role("button", name="Create sprint").click()
    expect(page).to_have_url(re.compile(r"/sprints/\d+$"))
    sprint_url = page.url
    expect(page.get_by_role("heading", name=f"Sprint 0002: {goal}")).to_be_visible()
    expect(page.get_by_text("Status: active")).to_be_visible()
    step("sprint-created-shares-sequence")

    page.get_by_label("Backlog issue").select_option(label=f"0001 {title}")
    page.get_by_role("button", name="Add issue").click()
    member = page.get_by_role("row").filter(has_text=title)
    expect(member).to_have_count(1)
    expect(member).to_contain_text("todo")
    step("issue-added-to-sprint")

    page.get_by_role("button", name="Close sprint").click()
    expect(page).to_have_url(re.compile(rf"/projects/{project_id}$"))
    step("sprint-closed-back-on-project")

    page.goto(sprint_url)
    expect(page.get_by_text("Status: closed")).to_be_visible()
    step("sprint-shows-closed")


def test_close_issue(user_page: Page, step: Step) -> None:
    page = user_page
    project_id = create_project(page, unique("E2E Close"))
    title = unique("Closable")
    issue_id = create_issue(page, project_id, title)

    page.goto(f"/issues/{issue_id}")
    page.get_by_role("button", name="Close issue").click()
    llm = page.get_by_label("Originating LLM")
    expect(page).to_have_url(re.compile(rf"/issues/{issue_id}$"))
    assert llm.evaluate("el => !el.validity.valid")
    expect(page.get_by_text("Status: backlog")).to_be_visible()
    step("close-without-llm-blocked")

    llm.fill("claude-e2e")
    page.get_by_label("Close note").fill("Closed by the e2e suite")
    page.get_by_role("button", name="Close issue").click()
    expect(page).to_have_url(re.compile(rf"/projects/{project_id}$"))
    expect(_issue_row(page, title)).to_contain_text("done")
    step("closed-issue-done-in-project")

    page.goto(f"/issues/{issue_id}")
    expect(page.get_by_text("Status: done")).to_be_visible()
    step("closed-issue-detail")


@pytest.mark.xfail(strict=True, reason=BUG_0019)
def test_close_issue_blank_llm_rejected(user_page: Page, step: Step) -> None:
    page = user_page
    project_id = create_project(page, unique("E2E Close blank"))
    issue_id = create_issue(page, project_id, unique("Blank LLM"))
    page.goto(f"/issues/{issue_id}")
    page.get_by_label("Originating LLM").fill("   ")
    page.get_by_role("button", name="Close issue").click()
    step("blank-llm-submitted")
    expect(page.get_by_text("Originating LLM is required to close an issue")).to_be_visible()
    page.goto(f"/issues/{issue_id}")
    expect(page.get_by_text("Status: backlog")).to_be_visible()


@pytest.mark.xfail(strict=True, reason=BUG_0019)
def test_closed_issue_metadata_and_reopen_blocked(user_page: Page, step: Step) -> None:
    page = user_page
    project_id = create_project(page, unique("E2E Immutable"))
    issue_id = create_issue(page, project_id, unique("Immutable"))
    page.goto(f"/issues/{issue_id}")
    page.get_by_label("Originating LLM").fill("claude-e2e")
    page.get_by_role("button", name="Close issue").click()
    page.goto(f"/issues/{issue_id}")
    step("closed-issue-detail")
    expect(page.get_by_text("claude-e2e")).to_be_visible()

    page.get_by_label("Originating LLM").fill("other-llm")
    page.get_by_role("button", name="Close issue").click()
    step("reclose-submitted")
    expect(page.get_by_text("Closed issue metadata is immutable")).to_be_visible()
