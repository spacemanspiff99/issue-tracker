"""W-AUTH: logout → protected page redirects to `/login` → bad password error → login."""

from __future__ import annotations

import re

from e2e_support import Step, admin_credentials
from playwright.sync_api import Page, expect


def test_auth(user_page: Page, step: Step) -> None:
    page = user_page
    step("logged-in-projects")

    page.get_by_role("button", name="Logout").click()
    expect(page).to_have_url(re.compile(r"/login$"))
    expect(page.get_by_role("heading", name="Login")).to_be_visible()
    step("logged-out")

    page.goto("/")
    expect(page).to_have_url(re.compile(r"/login$"))
    expect(page.get_by_role("heading", name="Projects")).to_have_count(0)
    step("protected-page-redirects-to-login")

    username, password = admin_credentials()
    page.get_by_label("Username").fill(username)
    page.get_by_label("Password").fill(password + "-wrong")
    page.get_by_role("button", name="Login").click()
    expect(page.locator(".error")).to_have_text("Invalid login")
    expect(page.get_by_role("heading", name="Projects")).to_have_count(0)
    step("bad-password-error")

    page.get_by_label("Username").fill(username)
    page.get_by_label("Password").fill(password)
    page.get_by_role("button", name="Login").click()
    expect(page).to_have_url(re.compile(r"/$"))
    expect(page.get_by_role("heading", name="Projects")).to_be_visible()
    step("logged-in-again")
