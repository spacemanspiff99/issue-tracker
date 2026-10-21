# Issue 0035: Document "Closed Issues Cannot Join A Sprint" In Tracker Guidance

Status: backlog
Recommended model: claude-opus-5-5 medium
Category gates: `IT-1`
Sprint: Sprint 0007

## Problem

Issue 0034 made `SprintService.add_issue` raise `DomainError("Closed issue cannot be added to a sprint")` for done+closed issues (web 400 inline, MCP raises). Its AC asks for the rule to be documented in `tracker-invariants`, but that lane's write scope excluded `.claude/`. Guidance changes need `guidance-change`.

## Files In Scope

- `.claude/skills/tracker-invariants/SKILL.md` (invariants table)
- `.claude/rules/services.md` (one-line invariant, optional)

## Acceptance Criteria

- [ ] `tracker-invariants` invariants table states: done+closed issues cannot be added to a sprint (`SprintService.add_issue`, unit test `test_adding_closed_issue_to_sprint_is_rejected_without_reopening`).
- [ ] `guidance-change` checks pass (placement, cross-references, mirror note).

## Category Checklists

`IT-1` Tracker State Integrity: Verify project-local sequence allocation, status transitions, dependency cycle rejection, and immutable close metadata.

## Verification Commands

```bash
python -m ruff check . && python -m pytest -q tests
```

## STOP

Stop once the guidance row lands. No code changes in this issue.
