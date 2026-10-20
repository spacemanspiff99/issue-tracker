---
name: ui-playwright
description: Use for any change a user can see or click — routes, templates, forms, redirects, setup/login, CSS — when writing acceptance criteria for such an issue, and before claiming a UI change works. Covers the Playwright Workflow Gate: AC written as named workflows, `tests/e2e/` tests that drive those workflows end to end, a screenshot at every step, and the evidence that must be reported.
---

# Playwright Workflow Gate

A UI change is verified only when Playwright has driven the affected workflows end to end
through a real browser against a migrated Postgres, asserted each step, and captured a
screenshot per step. Route tests, a 200, or clean logs are not this gate.

## 1. Acceptance criteria are workflows

Every issue that touches UI lists its workflows in AC, each as numbered user actions with an
expected result per step, and names the e2e test that covers it:

```
- [ ] W-ISSUE-CREATE (tests/e2e/test_issue_workflows.py::test_create_issue):
      1. Open project → issue form visible   2. Submit without AC → inline error, no issue
      3. Submit with AC → redirected to issue NNNN, AC shown
```

Include the failure path (validation error, rejected cycle, immutable close), not just the
happy path. A UI AC without a workflow + test name is incomplete — fix it before coding.

## 2. Core workflow catalog (regression set — every UI change runs all of it)

| Id | Workflow |
| --- | --- |
| W-SETUP | fresh DB `/` → `/setup` → admin created → `/setup` now redirects |
| W-AUTH | logout → protected page redirects to `/login` → bad password error → login |
| W-PROJECT | create project → appears in list → detail page |
| W-CATEGORY | add category to project → shown; not visible in another project |
| W-ISSUE-CREATE | create issue (missing-AC error, then success) → `NNNN` id shown |
| W-DEPENDENCY | add blocker → shown both sides; reverse edge rejected as cycle |
| W-SPRINT | create sprint (shares sequence) → add issue → close sprint |
| W-ISSUE-CLOSE | close without LLM → error; close with LLM → metadata shown; reopen blocked |

New user-facing feature → add its workflow row here (via `guidance-change`) and its test.

## 3. Test conventions (`tests/e2e/`)

- `deployment/scripts/remote-compose-deploy.sh` runs `pytest tests/e2e/` with
  `RUN_BROWSER_UAT=1`; tests skip unless that env var is set, so the default unit run stays fast.
- Target `E2E_BASE_URL` (default `http://localhost:8000`) — a live app on a migrated Postgres.
- `playwright.sync_api`, Chromium; use `PLAYWRIGHT_CHROMIUM_EXECUTABLE` when set
  (`/opt/pw-browsers/chromium` in cloud sessions). Viewports: desktop 1280×800 and mobile 390×844.
- One helper `step(page, name)` that asserts nothing itself but saves
  `artifacts/e2e/<test>/<NN>-<name>-<viewport>.png` (full page). Call it after **every** action.
- Assert per step with locators (`expect(page.get_by_role(...)).to_be_visible()`, URL, text,
  counts). The screenshot is evidence; the assertion is the pass/fail.
- Each test creates its own uniquely named data; never depend on test order or wipe the DB.
- `artifacts/` is gitignored.

## 4. Run it

Cloud session: start Postgres + migrate per `schema-change`, then
`DATABASE_URL=... APP_SECRET_KEY=x uvicorn issue_tracker.web.app:app --port 8000 &` and
`RUN_BROWSER_UAT=1 python -m pytest -q tests/e2e`.
Local/compose: `docker compose -f deployment/docker-compose.local.yml up -d` then the same pytest
command inside the app container.

## 5. Evidence (required before "done")

- Baseline: before changing UI, run the affected workflows on the base commit and keep the
  screenshots — they show what changed.
- After: full catalog run on the final commit; report pass count, commit SHA, and the
  screenshot folder.
- Review the screenshots of changed steps yourself (Read the PNG) — layout breakage passes
  locator assertions. Send the key before/after pairs to the user.
- Durable copy: CI uploads `artifacts/e2e/` as a workflow artifact; link it from the PR/issue.
