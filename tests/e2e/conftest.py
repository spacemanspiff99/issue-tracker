"""Playwright workflow suite (ui-playwright gate).

Runs only with RUN_BROWSER_UAT=1 against a live app on a migrated Postgres at E2E_BASE_URL.
Every step saves artifacts/e2e/<test>/<NN>-<name>-<viewport>.png; assertions decide pass/fail.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterator
from pathlib import Path

import pytest
from e2e_support import BASE_URL, Step, ensure_admin, login
from playwright.sync_api import Browser, Page, expect, sync_playwright

ARTIFACT_DIR = Path(os.environ.get("E2E_ARTIFACT_DIR", "artifacts/e2e"))
VIEWPORTS = {"desktop": {"width": 1280, "height": 800}, "mobile": {"width": 390, "height": 844}}


def pytest_collection_modifyitems(config, items):
    if os.environ.get("RUN_BROWSER_UAT") == "1":
        return
    skip = pytest.mark.skip(reason="browser UAT disabled; set RUN_BROWSER_UAT=1")
    for item in items:
        if Path(str(item.fspath)).parent == Path(__file__).parent:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def browser() -> Iterator[Browser]:
    with sync_playwright() as playwright:
        executable = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE") or None
        browser = playwright.chromium.launch(executable_path=executable)
        yield browser
        browser.close()


@pytest.fixture(params=list(VIEWPORTS))
def viewport(request) -> str:
    return request.param


@pytest.fixture()
def page(browser: Browser, viewport: str) -> Iterator[Page]:
    context = browser.new_context(base_url=BASE_URL, viewport=VIEWPORTS[viewport])
    context.set_default_timeout(10_000)
    page = context.new_page()
    yield page
    context.close()


@pytest.fixture()
def step(request, page: Page, viewport: str) -> Step:
    """Save a full-page screenshot for the current step. Asserts nothing itself."""
    test_name = re.sub(r"\[.*\]$", "", request.node.name)
    folder = ARTIFACT_DIR / test_name
    folder.mkdir(parents=True, exist_ok=True)
    counter = {"n": 0}

    def _step(name: str) -> None:
        counter["n"] += 1
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        page.screenshot(path=str(folder / f"{counter['n']:02d}-{slug}-{viewport}.png"), full_page=True)

    return _step


@pytest.fixture()
def user_page(page: Page) -> Page:
    ensure_admin(page)
    page.goto("/")
    if "/login" in page.url:
        login(page)
    expect(page.get_by_role("heading", name="Projects")).to_be_visible()
    return page
