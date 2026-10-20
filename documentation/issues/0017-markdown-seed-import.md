# Issue 0017: Import Markdown Issues And Sprints Into The Tracker

Status: backlog
Recommended model: claude-opus-5-5 low
Category gates: `IT-1`, `IT-2`
Sprint: Sprint 0007

## Problem

Until production is live, the tracker of record is markdown in `documentation/issues/` and `documentation/sprints/`. Cutover to `192.168.10.8` needs a repeatable way to seed a project from those files without hand entry or broken sequence IDs.

## Scope

- New CLI command `issue-tracker import-markdown` in `src/issue_tracker/cli.py`, calling the service layer only (no direct store writes, no duplicated lifecycle logic).
- Imports `documentation/issues/*.md` and `documentation/sprints/*.md` into a named project.
- Preserves the `NNNN` sequence number, title, status, acceptance criteria (checked state), sprint membership, and maps `Category gates` to project categories (created as project data, not hardcoded).
- `--dry-run` prints what would be created/updated and writes nothing.
- Idempotent: a re-run creates no duplicates and reports 0 changes when nothing changed.

## Acceptance Criteria

- [ ] `import-markdown --dry-run` on this repo lists every issue and sprint and writes nothing (verified by row counts before/after).
- [ ] Real run creates one tracker issue per markdown issue with matching `NNNN`, title, status, and AC.
- [ ] Categories come from each file's `Category gates`, created per project; no `IT-*` literal in app logic.
- [ ] Second run reports 0 created / 0 updated.
- [ ] Unit tests cover parse, dry-run, import, and idempotent re-run; `python -m ruff check . && python -m pytest -q tests` green.

## Category Checklists

`IT-1` Tracker State Integrity: sequence IDs, status transitions, and close metadata go through the service layer; next allocated ID is above the highest imported one.
`IT-2` Category And AC Binding: categories are project-scoped data; AC stay bound to their issue.

## Verification Commands

```bash
python -m ruff check . && python -m pytest -q tests
issue-tracker import-markdown --project issue-tracker --dry-run
```

## STOP

Stop when every AC passes with evidence. Do not run against `192.168.10.8`; the production seed is an owner step in `documentation/guides/production-cutover.md`.
