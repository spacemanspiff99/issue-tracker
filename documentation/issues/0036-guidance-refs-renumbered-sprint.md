# Issue 0036: Point Guidance And README At Renumbered Sprint 0035

Status: in-progress
Recommended model: claude-opus-5-5 medium
Category gates: `IT-1`
Sprint: Sprint 0007

## Problem

Issue 0033 renumbered the old Sprint 0008 to Sprint 0035 (`documentation/sprints/0035-subagent-local-uat-quality-iteration.md`). Three references outside `documentation/` still point at the old number and were outside that lane's write scope (`documentation/` only):

- `CLAUDE.md:89` — skill index row "running sprint 0007/0008 work".
- `.claude/skills/uat-gate/SKILL.md:3` and `:8` — "sprint 0007/0008" / "sprints 0007/0008". After the rename, "0008" there reads as Issue 0008, not the sprint.
- `README.md:51` — links `documentation/sprints/0008-subagent-local-uat-quality-iteration.md`, which no longer exists.

Files in scope: `CLAUDE.md`, `.claude/skills/uat-gate/SKILL.md`, `README.md`. Load `guidance-change` before editing the first two.

## Acceptance Criteria

- [x] `CLAUDE.md` and `.claude/skills/uat-gate/SKILL.md` say sprints 0007/0035; issue references (0008–0012) are unchanged. Evidence (f84d060): `CLAUDE.md:90` "running sprint 0007/0035 work"; `uat-gate/SKILL.md:3,8` "sprint 0007/0035" / "sprints 0007/0035"; `SKILL.md:9` "Issues: 0008 runtime gate …" untouched.
- [x] `README.md` links `documentation/sprints/0035-subagent-local-uat-quality-iteration.md`. Evidence (f84d060): `README.md:51`; `test -f documentation/sprints/0035-subagent-local-uat-quality-iteration.md` → exit 0.
- [x] `grep -rnE "sprints?[ /]0007/0008|sprints/0008-" CLAUDE.md .claude README.md` prints nothing. Evidence (f84d060): no output, exit 1.
- [x] `python -m ruff check . && python -m pytest -q tests` green. Evidence (f84d060): `All checks passed!`; `54 passed, 22 skipped`.

## Category Checklists

`IT-1` Tracker State Integrity: Verify project-local sequence allocation, status transitions, dependency cycle rejection, and immutable close metadata.

## Verification Commands

```bash
grep -rnE "sprints?[ /]0007/0008|sprints/0008-" CLAUDE.md .claude README.md
test -f documentation/sprints/0035-subagent-local-uat-quality-iteration.md
```

## STOP

Stop when the grep prints nothing. Don't touch Issue 0008 references or historical evidence lines in closed/in-progress issues.

Status: AC met on branch `claude/0036-guidance-refs-renumbered-sprint` (f84d060). Close (`Status: done`) when the PR merges with CI green. Originating model: claude-opus-5-5 (effort: medium).
