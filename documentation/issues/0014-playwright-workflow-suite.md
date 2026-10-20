# Issue 0014: Playwright Workflow Suite With Step Screenshots

Status: backlog
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

## Category Checklists

`IT-1` Tracker State Integrity: Verify project-local sequence allocation, status transitions, dependency cycle rejection, and immutable close metadata.

`IT-5` Auth And Secret Safety: Verify password hashing, session flags, setup flow, secret handling, and no credential logging.

`IT-6` Deployment And Configuration Drift: Verify compose files, env vars, health checks, explicit migrations, and workflow behavior stay aligned.

## Verification Commands

See `.claude/skills/ui-playwright/SKILL.md` (Run it).

## STOP

Stop when the suite and CI artifact are green, or record the failing workflow step with its screenshot.
