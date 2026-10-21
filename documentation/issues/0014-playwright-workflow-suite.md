# Issue 0014: Playwright Workflow Suite With Step Screenshots

Status: in-progress (merged in #10, 680169a; last AC unverified)
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

- [x] Every catalog workflow has a test whose steps match the catalog, including its failure path. Evidence: `grep -n "def test_" tests/e2e/*.py` at `b6a0092` lists all 11 tests in the map below; 0019 (#12, a98b164) removed the strict xfails, so every failure path now runs as a normal test.
- [x] Every step asserts with a locator/URL/text check and saves a full-page screenshot. Evidence: 38 `step(` calls vs 60 `expect(`/`assert` lines across `tests/e2e/test_*.py` (each `step()` preceded by its assertions); CI run 39458603486 collected 72 PNGs.
- [x] `RUN_BROWSER_UAT=1 python -m pytest tests/e2e` passes against a fresh migrated stack; tests skip without the env var. Evidence: CI `e2e` job on `b6a0092` (fresh compose volume → `alembic upgrade head` → health) → `22 passed in 19.18s`; locally without the env var `python -m pytest -q tests` → `48 passed, 22 skipped`.
- [x] CI e2e job is green and its artifact contains a screenshot per step per viewport. Evidence: run 39458603486 job `e2e` success on `b6a0092`; "Collect screenshots" counted `72`; artifact `e2e-screenshots` (id 12280459718, 2.4 MB) uploaded. 22 passed = 11 tests × 2 viewports.
- [ ] `RUN_BROWSER_UAT=1` path in `remote-compose-deploy.sh` runs the suite successfully on a compose stack. **Not verified.** CI runs the same `exec app python -m pytest tests/e2e/` command but not the script. No `local-pipeline.yml` run since #10 merged (latest run 2026-05-26). 2026-10-21 cloud attempt (script run against localhost through a local `ssh` stand-in, `DEPLOY_ENV=uat`) failed twice in `docker compose build` because the sandbox's TLS proxy breaks pip, apt and the Playwright download inside the build. That's a sandbox limit, not a repo defect. Needs one self-hosted-runner run with `run_browser_uat: true` against dev/UAT (owner-approved dispatch).

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
- CI `e2e` job (compose stack + same `exec app python -m pytest tests/e2e/` as the deploy script): green on `main` `b6a0092`, run 39458603486, `22 passed`, 72 screenshots.

## Category Checklists

`IT-1` Tracker State Integrity: Verify project-local sequence allocation, status transitions, dependency cycle rejection, and immutable close metadata.

`IT-5` Auth And Secret Safety: Verify password hashing, session flags, setup flow, secret handling, and no credential logging.

`IT-6` Deployment And Configuration Drift: Verify compose files, env vars, health checks, explicit migrations, and workflow behavior stay aligned.

## Verification Commands

See `.claude/skills/ui-playwright/SKILL.md` (Run it).

## STOP

Stop when the suite and CI artifact are green, or record the failing workflow step with its screenshot.

Remaining: the last AC needs one owner-approved `local-pipeline.yml` run with `run_browser_uat: true` to dev or UAT (never `promote_prod`, see Issue 0038). Then tick it with the run URL and set `Status: done`.
