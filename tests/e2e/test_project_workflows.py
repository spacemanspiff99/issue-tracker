"""W-PROJECT and W-CATEGORY."""

from __future__ import annotations

import re

from e2e_support import Step, create_project, unique
from playwright.sync_api import Page, expect


def test_project(user_page: Page, step: Step) -> None:
    page = user_page
    name = unique("E2E Project")
    page.get_by_label("Name").fill(name)
    page.get_by_label("Repo URL").fill("https://example.invalid/e2e.git")
    step("project-form-filled")

    page.get_by_role("button", name="Create project").click()
    expect(page).to_have_url(re.compile(r"/projects/\d+$"))
    expect(page.get_by_role("heading", name=name)).to_be_visible()
    step("project-detail-after-create")

    page.get_by_role("link", name="Projects").click()
    link = page.get_by_role("link", name=name, exact=True)
    expect(link).to_have_count(1)
    step("project-in-list")

    link.click()
    expect(page.get_by_role("heading", name=name)).to_be_visible()
    expect(page.get_by_role("heading", name="Create issue")).to_be_visible()
    step("project-detail-from-list")


def test_category(user_page: Page, step: Step) -> None:
    page = user_page
    first = create_project(page, unique("E2E Cat A"))
    second = create_project(page, unique("E2E Cat B"))
    key = unique("E2E").replace(" ", "-").upper()
    name = unique("Browser checks")

    page.goto(f"/projects/{first}")
    page.get_by_label("Key").fill(key)
    page.get_by_label("Name").fill(name)
    page.get_by_label("Checklist").fill("Screenshot every step")
    step("category-form-filled")

    page.get_by_role("button", name="Add category").click()
    expect(page).to_have_url(re.compile(rf"/projects/{first}$"))
    expect(page.get_by_role("listitem").filter(has_text=f"{key}: {name}")).to_have_count(1)
    expect(page.get_by_label("Category").locator("option", has_text=key)).to_have_count(1)
    step("category-shown-in-project")

    page.goto(f"/projects/{second}")
    expect(page.get_by_role("heading", name="Categories")).to_be_visible()
    expect(page.get_by_text(key)).to_have_count(0)
    expect(page.get_by_label("Category").locator("option", has_text=key)).to_have_count(0)
    step("category-absent-in-other-project")
