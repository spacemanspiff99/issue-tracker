# Issue 0037: Document "Closed Issues Cannot Join A Sprint" In Tracker Guidance

Status: in-progress
Recommended model: claude-opus-5-5 medium
Category gates: `IT-1`
Sprint: Sprint 0007

## Problem

Issue 0034 made `SprintService.add_issue` raise `DomainError("Closed issue cannot be added to a sprint")` for done+closed issues (web 400 inline, MCP raises). Its AC asks for the rule to be documented in `tracker-invariants`, but that lane's write scope excluded `.claude/`. Guidance changes need `guidance-change`.

## Files In Scope

- `.claude/skills/tracker-invariants/SKILL.md` (invariants table)
- `.claude/rules/services.md` (one-line invariant, optional)

## Acceptance Criteria

- [x] `tracker-invariants` invariants table states: done+closed issues cannot be added to a sprint (`SprintService.add_issue`, unit test `test_adding_closed_issue_to_sprint_is_rejected_without_reopening`). Evidence (fe98852): new row after the close-metadata row in `.claude/skills/tracker-invariants/SKILL.md`; `.claude/rules/services.md` close line extended (19 lines, ≤ 20).
- [x] `guidance-change` checks pass (placement, cross-references, mirror note). Evidence (fe98852): placement = skill table (procedure layer) + one clause in the path-scoped rule, no `CLAUDE.md` change; cited names exist — `grep -n "def add_issue" src/issue_tracker/services/tracker.py` → `:332`, `grep -n "def test_adding_closed_issue_to_sprint_is_rejected_without_reopening" tests/unit/test_services.py` → `:109`, web 400 `tests/integration/test_web_routes.py:189`, MCP raise `tests/integration/test_mcp_tools.py:46`; no skill added/renamed, so index unchanged; `mirror-rules.yml` publishes `.claude/` on merge to `main`. `python -m ruff check . && python -m pytest -q tests` → `All checks passed!`, `54 passed, 22 skipped`.

## Category Checklists

`IT-1` Tracker State Integrity: Verify project-local sequence allocation, status transitions, dependency cycle rejection, and immutable close metadata.

## Verification Commands

```bash
python -m ruff check . && python -m pytest -q tests
```

## STOP

Stop once the guidance row lands. No code changes in this issue.

Status: AC met on branch `claude/0037-document-sprint-add-closed-issue-rule` (fe98852). Close (`Status: done`) when the PR merges with CI green. Originating model: claude-opus-5-5 (effort: medium).
