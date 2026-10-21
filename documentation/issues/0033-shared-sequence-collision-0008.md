# Issue 0033: Resolve Shared-Sequence Collision On 0008

Status: in-progress
Recommended model: claude-opus-5-5 medium
Category gates: `IT-1`
Sprint: Sprint 0007

## Problem

Issues and sprints share one `NNNN` sequence, but `documentation/issues/0008-local-runtime-gate.md` and `documentation/sprints/0008-subagent-local-uat-quality-iteration.md` both use `0008`. `issue-tracker import-markdown` (Issue 0017) correctly refuses the tree (`Sequence 0008 used by ...`), so the repo can't be seeded until one is renumbered. Found during 0017; outside that lane's write scope.

## Acceptance Criteria

- [ ] Sprint 0008 is renumbered to the next free ID (file name, `# Sprint NNNN:` header) and every reference to "Sprint 0008" in `documentation/`, `CLAUDE.md`, and `.claude/` is updated. `Issue 0008` references stay as they are. **Partly met at a495801; blocked by Issue 0036 for the rest.** Next free ID was 0035 (the highest ID was 0034). `git mv` → `documentation/sprints/0035-subagent-local-uat-quality-iteration.md`, with its header and its two self-references updated. `grep -rn "Sprint 0008" documentation CLAUDE.md .claude` → only the issue 0033 and 0036 text that describes the rename. The lowercase `sprint 0007/0008` in `CLAUDE.md:89` and `.claude/skills/uat-gate/SKILL.md:3,8`, plus the `README.md:51` link, are outside the `documentation/`-only write scope and are filed as Issue 0036. Issue 0017's historical `sprints/0008-*` evidence line is left as written.
- [x] `issue-tracker import-markdown --project issue-tracker --dry-run` against an empty DB exits 0 and lists every issue and sprint. Evidence at a495801: ran on an empty Postgres 16 DB after `alembic upgrade head` (to `0004_reconcile_schema_drift`), with `DATABASE_URL` set. Exit 0, `dry-run: would have 23 created / 0 updated / 0 unchanged`. That is 1 project, 6 categories, sprints 0007 and 0035, and all 14 issue files. Row counts before and after: 0 in projects, issues, sprints, categories, sprint_issues and issue_events. Before the fix, `main` b6a0092 exits 1 with `Sequence 0008 used by ...`.
- [x] `python -m ruff check . && python -m pytest -q tests` green. Evidence at a495801: `All checks passed!` and `49 passed, 22 skipped`. The 22 skips are all `tests/e2e`, which reports "browser UAT disabled; set RUN_BROWSER_UAT=1".

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

Result (a495801): the duplicate check prints nothing and the dry run exits 0. This issue stays `in-progress` until Issue 0036 lands the out-of-scope references for AC 1. Originating model: claude-opus-5-5 (effort: medium).

Note: the verification command `ls documentation/issues documentation/sprints | cut -c1-4 | sort | uniq -d` also prints `docu`, because `ls` puts a `documentation/...:` header above each directory. The evidence above uses `ls ... | grep -oE '^[0-9]{4}' | sort | uniq -d` instead.
