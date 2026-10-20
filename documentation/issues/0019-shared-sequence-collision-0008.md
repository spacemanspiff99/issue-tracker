# Issue 0019: Resolve Shared-Sequence Collision On 0008

Status: backlog
Recommended model: claude-opus-5-5 medium
Category gates: `IT-1`
Sprint: Sprint 0007

## Problem

Issues and sprints share one `NNNN` sequence, but `documentation/issues/0008-local-runtime-gate.md` and `documentation/sprints/0008-subagent-local-uat-quality-iteration.md` both use `0008`. `issue-tracker import-markdown` (Issue 0017) correctly refuses the tree (`Sequence 0008 used by ...`), so the repo can't be seeded until one is renumbered. Found during 0017; outside that lane's write scope.

## Acceptance Criteria

- [ ] Sprint 0008 is renumbered to the next free ID (file name, `# Sprint NNNN:` header) and every reference to "Sprint 0008" in `documentation/`, `CLAUDE.md`, and `.claude/` is updated. `Issue 0008` references stay as they are.
- [ ] `issue-tracker import-markdown --project issue-tracker --dry-run` against an empty DB exits 0 and lists every issue and sprint.
- [ ] `python -m ruff check . && python -m pytest -q tests` green.

## Category Checklists

`IT-1` Tracker State Integrity: Verify project-local sequence allocation, status transitions, dependency cycle rejection, and immutable close metadata.

## Verification Commands

```bash
ls documentation/issues documentation/sprints | cut -c1-4 | sort | uniq -d   # prints nothing
grep -rn "Sprint 0008" documentation CLAUDE.md .claude
issue-tracker import-markdown --project issue-tracker --dry-run
```

## STOP

Stop when the duplicate check prints nothing and the dry run exits 0. Renumber the sprint, not the issue: issue 0008 is referenced by ID across Sprint 0007 and the UAT docs.
