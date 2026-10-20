# Issue 0014: Playwright Workflow Suite With Step Screenshots

Status: in-progress
Recommended model: claude-opus-5-5 medium
Category gates: `IT-1`, `IT-5`, `IT-6`
Sprint: Sprint 0007

## Problem

No browser tests exist. `deployment/scripts/remote-compose-deploy.sh` runs `pytest tests/e2e/` when `RUN_BROWSER_UAT=1`, but `tests/e2e/` is missing and the Docker image has no Playwright browser, so UAT browser verification cannot pass. The `ui-playwright` skill defines the required gate.

## Scope

- `tests/e2e/` with the `step()` screenshot helper and one test per workflow in the `ui-playwright` catalog (W-SETUP … W-ISSUE-CLOSE), desktop and mobile viewports.
- Chromium available to the app image (or a separate e2e image) so the deploy script's browser UAT runs.
- CI job: Postgres service → migrate → start app → run e2e → upload `artifacts/e2e/` as a workflow artifact (always, including on failure).

## Acceptance Criteria

- [ ] Every catalog workflow has a test whose steps match the catalog, including its failure path.
- [ ] Every step asserts with a locator/URL/text check and saves a full-page screenshot.
- [ ] `RUN_BROWSER_UAT=1 python -m pytest tests/e2e` passes against a fresh migrated stack; tests skip without the env var.
- [ ] CI e2e job is green and its artifact contains a screenshot per step per viewport.
- [ ] `RUN_BROWSER_UAT=1` path in `remote-compose-deploy.sh` runs the suite successfully on a compose stack.

## Workflow → test map

| Workflow | Test (`tests/e2e/`) | Failure path |
| --- | --- | --- |
| W-SETUP | `test_00_setup.py::test_setup` | `/setup` redirects once admin exists |
| W-AUTH | `test_auth_workflows.py::test_auth` | protected page → `/login`; bad password → "Invalid login" |
| W-PROJECT | `test_project_workflows.py::test_project` | — |
| W-CATEGORY | `test_project_workflows.py::test_category` | category absent from another project |
| W-ISSUE-CREATE | `test_issue_workflows.py::test_create_issue` | empty AC blocked by browser; blank AC → server error |
| W-DEPENDENCY | `test_issue_workflows.py::test_dependency`, `::test_dependency_cycle_rejected` | cycle → **500, strict xfail → Issue 0019** |
| W-SPRINT | `test_issue_workflows.py::test_sprint` | — |
| W-ISSUE-CLOSE | `test_issue_workflows.py::test_close_issue`, `::test_close_issue_blank_llm_rejected`, `::test_closed_issue_metadata_and_reopen_blocked` | empty LLM blocked by browser; **blank LLM closes issue, metadata not shown, reopen not guarded → strict xfail → Issue 0019** |

Each test runs at desktop 1280×800 and mobile 390×844. W-SETUP's fresh-DB steps run once per stack
(first viewport); the other viewport records the post-setup redirect.

## Evidence

- Local (cloud session, Postgres 16 + `alembic upgrade head` on an empty DB, uvicorn, Chromium):
  `RUN_BROWSER_UAT=1 python -m pytest -q tests/e2e` → `16 passed, 6 xfailed`; 70 screenshots.
- Without the env var: `python -m pytest -q tests` → `12 passed, 22 skipped`.
- CI `e2e` job (compose stack + same `exec app python -m pytest tests/e2e/` as the deploy script): see PR.

## Category Checklists

`IT-1` Tracker State Integrity: Verify project-local sequence allocation, status transitions, dependency cycle rejection, and immutable close metadata.

`IT-5` Auth And Secret Safety: Verify password hashing, session flags, setup flow, secret handling, and no credential logging.

`IT-6` Deployment And Configuration Drift: Verify compose files, env vars, health checks, explicit migrations, and workflow behavior stay aligned.

## Verification Commands

See `.claude/skills/ui-playwright/SKILL.md` (Run it).

## STOP

Stop when the suite and CI artifact are green, or record the failing workflow step with its screenshot.
