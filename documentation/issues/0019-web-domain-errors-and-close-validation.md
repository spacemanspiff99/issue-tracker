# Issue 0019: Web Routes 500 On Domain Errors; Blank LLM Closes Issues; Close Metadata Hidden

Status: backlog
Recommended model: claude-opus-5-5 high
Category gates: `IT-1`, `IT-5`
Sprint: Sprint 0007

## Problem

Found by the Issue 0014 Playwright suite (strict-xfail tests in `tests/e2e/test_issue_workflows.py`):

1. `POST /issues/{id}/dependencies` with a reverse edge raises `DomainError("Dependency would create a cycle")`
   uncaught → **500 Internal Server Error** page. Same pattern in `close_issue`, `create_category`,
   `create_sprint`, `add_sprint_issue` (no `DomainError` handling in `web/app.py`).
2. `IssueService.update_status` checks `if not originating_llm`, so a whitespace LLM (`"   "` passes the
   browser `required` check) **closes the issue with a blank originating LLM** — IT-1 close-metadata violation.
3. `issue_detail.html` shows no close metadata (originating LLM, closed by, note, closed at) and still renders
   the close form on a closed issue; re-closing is silently ignored instead of reporting
   "Closed issue metadata is immutable". There is no reopen control to verify "reopen blocked".

Evidence: CI `e2e` job artifact `e2e-screenshots`, folders `test_dependency_cycle_rejected/`,
`test_close_issue_blank_llm_rejected/`, `test_closed_issue_metadata_and_reopen_blocked/`.

## Scope

`src/issue_tracker/web/app.py`, `src/issue_tracker/web/templates/issue_detail.html`,
`src/issue_tracker/services/tracker.py` (strip/validate `originating_llm`), route tests, then remove the
`xfail` markers from the three e2e tests.

## Acceptance Criteria

- [ ] W-DEPENDENCY (`tests/e2e/test_issue_workflows.py::test_dependency_cycle_rejected`): reverse edge →
      inline "Dependency would create a cycle" on the issue page, no 500, no new edge.
- [ ] W-ISSUE-CLOSE (`::test_close_issue_blank_llm_rejected`): whitespace LLM → inline
      "Originating LLM is required to close an issue", issue stays `backlog`.
- [ ] W-ISSUE-CLOSE (`::test_closed_issue_metadata_and_reopen_blocked`): closed issue detail shows originating
      LLM; re-close attempt → "Closed issue metadata is immutable" shown, metadata unchanged.
- [ ] Every `DomainError` from a web route re-renders with an inline error (route tests per route).
- [ ] `xfail` markers removed; `RUN_BROWSER_UAT=1 python -m pytest tests/e2e` fully green.

## Category Checklists

`IT-1` Tracker State Integrity: Verify project-local sequence allocation, status transitions, dependency cycle rejection, and immutable close metadata.

`IT-5` Auth And Secret Safety: Verify password hashing, session flags, setup flow, secret handling, and no credential logging.

## Verification Commands

`python -m ruff check . && python -m pytest -q tests`, then the `ui-playwright` run (§4).

## STOP

Stop when the three e2e tests pass without `xfail` (strict xfail turns them red once fixed — remove the marker
in the same PR).
