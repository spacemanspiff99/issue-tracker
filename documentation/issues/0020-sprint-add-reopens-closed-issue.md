# Issue 0020: Adding A Closed Issue To A Sprint Reopens It

Status: backlog
Recommended model: claude-opus-5-5 medium
Category gates: `IT-1`
Sprint: Sprint 0007

## Problem

`SprintService.add_issue` sets `issue.status = in-progress` unconditionally. On a done+closed issue this leaves `status=in-progress` with `closed_at` still set, which breaks "done+closed is final". Repro: create issue → `update_status(done, originating_llm=...)` → `add_issue(sprint, issue)` → status `in-progress`, `closed_at` not null. Found during 0017 (the importer avoids this path); outside that lane's write scope.

## Acceptance Criteria

- [ ] `add_issue` on a done+closed issue either raises `DomainError` or adds membership without changing status (pick one, document it in `tracker-invariants`).
- [ ] Unit test in `tests/unit/test_services.py` covers the closed-issue case.
- [ ] Web and MCP sprint-add paths show the same behavior (parity check).
- [ ] `python -m ruff check . && python -m pytest -q tests` green.

## Category Checklists

`IT-1` Tracker State Integrity: Verify project-local sequence allocation, status transitions, dependency cycle rejection, and immutable close metadata.

## Verification Commands

```bash
python -m ruff check . && python -m pytest -q tests
```

## STOP

Stop when the closed-issue test passes on both surfaces. Do not change backlog → in-progress behavior for open issues.
