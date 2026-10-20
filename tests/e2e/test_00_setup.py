"""W-SETUP: fresh DB `/` → `/setup` → admin created → `/setup` now redirects.

Named test_00_* so a fresh stack exercises the first-run path before any fixture creates the admin.
On an already set-up stack only the redirect steps can be observed.
"""

from __future__ import annotations

import re

from e2e_support import Step, admin_credentials
from playwright.sync_api import Page, expect


def test_setup(page: Page, step: Step) -> None:
    page.goto("/")
    if page.url.endswith("/setup"):
        expect(page.get_by_role("heading", name="First-run setup")).to_be_visible()
        step("fresh-root-redirects-to-setup")

        username, password = admin_credentials()
        page.get_by_label("Username").fill(username)
        page.get_by_label("Password").fill(password)
        step("setup-form-filled")
        page.get_by_role("button", name="Create admin").click()
        expect(page).to_have_url(re.compile(r"/$"))
        expect(page.get_by_role("heading", name="Projects")).to_be_visible()
        step("admin-created-projects-shown")
    else:
        expect(page).to_have_url(re.compile(r"/login$"))
        expect(page.get_by_role("heading", name="Login")).to_be_visible()
        step("already-setup-root-redirects-to-login")

    page.goto("/setup")
    expect(page).to_have_url(re.compile(r"/login$"))
    expect(page.get_by_role("heading", name="First-run setup")).to_have_count(0)
    step("setup-now-redirects")
