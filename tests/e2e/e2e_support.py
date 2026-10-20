"""Shared helpers for the Playwright workflow suite (see conftest.py)."""

from __future__ import annotations

import os
import uuid
from collections.abc import Callable

from playwright.sync_api import Page, expect

BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:8000").rstrip("/")

Step = Callable[[str], None]


def admin_credentials() -> tuple[str, str]:
    username = os.environ.get("E2E_ADMIN_USERNAME") or os.environ.get("ADMIN_USERNAME") or "admin"
    password = (
        os.environ.get("E2E_ADMIN_PASSWORD") or os.environ.get("ADMIN_INITIAL_PASSWORD") or "e2e-local-password"
    )
    return username, password


def unique(prefix: str) -> str:
    return f"{prefix} {uuid.uuid4().hex[:8]}"


def ensure_admin(page: Page) -> None:
    """Create the admin through /setup on a fresh stack; no-op once setup is done."""
    page.goto("/setup")
    if page.url.endswith("/setup"):
        username, password = admin_credentials()
        page.get_by_label("Username").fill(username)
        page.get_by_label("Password").fill(password)
        page.get_by_role("button", name="Create admin").click()
        expect(page.get_by_role("heading", name="Projects")).to_be_visible()


def login(page: Page) -> None:
    username, password = admin_credentials()
    page.goto("/login")
    page.get_by_label("Username").fill(username)
    page.get_by_label("Password").fill(password)
    page.get_by_role("button", name="Login").click()
    expect(page.get_by_role("heading", name="Projects")).to_be_visible()


def create_project(page: Page, name: str) -> int:
    page.goto("/")
    page.get_by_label("Name").fill(name)
    page.get_by_role("button", name="Create project").click()
    expect(page.get_by_role("heading", name=name)).to_be_visible()
    return int(page.url.rstrip("/").rsplit("/", 1)[1])


def create_issue(page: Page, project_id: int, title: str, criteria: str = "Works end to end") -> int:
    page.goto(f"/projects/{project_id}")
    page.get_by_label("Title").fill(title)
    page.get_by_label("Acceptance criteria").fill(criteria)
    page.get_by_role("button", name="Create issue").click()
    link = page.get_by_role("link", name=title, exact=True)
    expect(link).to_be_visible()
    return int(link.get_attribute("href").rsplit("/", 1)[1])
