# Issue 0017: Import Markdown Issues And Sprints Into The Tracker

Status: in-progress (blocked on Issue 0019 for the full-repo run)
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

- [ ] `import-markdown --dry-run` on this repo lists every issue and sprint and writes nothing (verified by row counts before/after). **Blocked by Issue 0019:** the repo tree has `0008` as both an issue and a sprint, and the importer refuses it (`import-markdown: Sequence 0008 used by ...`, exit 1). On a copy without `sprints/0008-*`: 18 actions listed, row counts 0 → 0 across projects/categories/issues/sprints/sprint_issues/issue_events.
- [ ] Real run creates one tracker issue per markdown issue with matching `NNNN`, title, status, and AC. **Blocked by Issue 0019** for this repo. On the same copy: 10 issues `0008`–`0018` with matching title/status/AC, `next_sequence` 19; `test_import_preserves_sequence_title_status_ac_and_sprint` covers it.
- [x] Categories come from each file's `Category gates`, created per project; no `IT-*` literal in app logic. Names/checklists come from each file's `Category Checklists` (6 `IT-*` rows created); `grep -rn "IT-[0-9]" src/issue_tracker` → none; `test_categories_are_project_scoped...` passes.
- [x] Second run reports 0 created / 0 updated. Copy rerun: `0 created / 0 updated / 17 unchanged`, row counts unchanged; `test_second_run_reports_no_changes`, `test_cli_dry_run_import_and_rerun`.
- [x] Unit tests cover parse, dry-run, import, and idempotent re-run; `python -m ruff check . && python -m pytest -q tests` green (38 passed).

## Implementation Notes

- `src/issue_tracker/markdown_import.py` parses and diffs the files; every write goes through `ProjectService`/`CategoryService`/`IssueService`/`SprintService`.
- Added to the service layer: `create_issue(..., sequence=)` and `create_sprint(..., sequence=, status=)` (an explicit sequence is rejected if any issue or sprint already uses it, and `next_sequence` is raised above it), `IssueService.update_details`, plus sprint/project lookups. Web and MCP don't expose explicit sequences: that's import-only by design.
- Free-text status lines are normalized by prefix (`in review ...` → `in-progress`, `closed` → `done`); anything else fails with the file path.
- Primary category = first `Category gates` key; all gate keys are stored in `labels`.
- Closed issues are never re-added to a sprint (that would trip Issue 0020).
- Found and recorded outside this lane's scope: Issue 0019 (0008 collision), Issue 0020 (`add_issue` reopens closed issues).

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
