# Issue 0034: Adding A Closed Issue To A Sprint Reopens It

Status: in-progress
Recommended model: claude-opus-5-5 medium
Category gates: `IT-1`
Sprint: Sprint 0007

## Problem

`SprintService.add_issue` sets `issue.status = in-progress` unconditionally. On a done+closed issue this leaves `status=in-progress` with `closed_at` still set, which breaks "done+closed is final". Repro: create issue → `update_status(done, originating_llm=...)` → `add_issue(sprint, issue)` → status `in-progress`, `closed_at` not null. Found during 0017 (the importer avoids this path); outside that lane's write scope.

## Acceptance Criteria

- [x] `add_issue` on a done+closed issue either raises `DomainError` or adds membership without changing status (pick one, document it in `tracker-invariants`). — Chose **raise** `DomainError("Closed issue cannot be added to a sprint")`; no membership, status and `closed_at` unchanged. Documenting it in `tracker-invariants` was outside this lane's write scope (`.claude/`) → Issue 0035.
- [x] Unit test in `tests/unit/test_services.py` covers the closed-issue case. — `test_adding_closed_issue_to_sprint_is_rejected_without_reopening` (red before fix, green after; also asserts open issue still goes backlog → in-progress).
- [x] Web and MCP sprint-add paths show the same behavior (parity check). — `test_sprint_add_closed_issue_renders_inline_error_and_keeps_it_closed` (web 400 + inline error, issue stays done) and `test_mcp_sprint_add_rejects_closed_issue_like_web` (`sprint.add_issue` raises the same `DomainError`). Both call `SprintService.add_issue`; no adapter logic.
- [x] `python -m ruff check . && python -m pytest -q tests` green. — `All checks passed!`; `52 passed, 22 skipped` (skips = browser UAT, `RUN_BROWSER_UAT` unset).

## Category Checklists

`IT-1` Tracker State Integrity: Verify project-local sequence allocation, status transitions, dependency cycle rejection, and immutable close metadata.

## Verification Commands

```bash
python -m ruff check . && python -m pytest -q tests
```

## STOP

Stop when the closed-issue test passes on both surfaces. Do not change backlog → in-progress behavior for open issues.

Status: code + tests done on branch `claude/0034-sprint-add-closed-issue`; guidance documentation split to Issue 0035. Close (`Status: done`) when the PR merges with CI green. Originating model: claude-opus-5-5 (effort: medium).
