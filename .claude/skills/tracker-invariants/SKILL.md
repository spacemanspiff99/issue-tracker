---
name: tracker-invariants
description: Use when changing `services/tracker.py`, `repositories/store.py`, or domain enums — sequence/ID allocation, issue or sprint status transitions, dependencies and cycle checks, close metadata, categories and checklists, issue-log entries, import/export (`cli.py`). Covers IT-1 (tracker state integrity) and IT-2 (category and AC binding), plus web/MCP parity.
---

# Tracker Invariants (IT-1, IT-2)

## Invariants the code must keep

| Invariant | Where enforced | Test home |
| --- | --- | --- |
| Issues + sprints share one per-project sequence; shown as `NNNN` | `repo.allocate_sequence`, `display_id` | `tests/unit/test_services.py` |
| Status values `backlog`/`in-progress`/`done` (`IssueStatus`); order not enforced; done+closed is final | `IssueService.update_status` | unit |
| Close requires `originating_llm`; sets `closed_at`, `closed_by`, `close_note` once | `update_status` | unit |
| Dependencies: no self-edge, no duplicate, no cycle, same project | `IssueService.add_dependency`/`_path_exists` | unit |
| AC required on create | `IssueService.create_issue` | unit |
| Categories are project rows (issue's category must be same project); no peer taxonomy constants | `CategoryService` | `test_categories_are_project_scoped_not_peer_taxonomy_constants` |
| Issue create, status change, sprint add record an `issue_events` row (`add_dependency` doesn't yet — gap) | `record_event` | none yet |
| Import requires explicit `--category-map` when source has categories | `cli.py` | `tests/integration/test_cli_import_export.py` |

## Workflow

1. Write/extend the unit test first; run it red.
2. Implement in the service (repository for queries). Raise `DomainError` for rule violations.
3. Only then wire web (`web-auth`) and MCP (`mcp-contract`) — both call the same service method.
   If a route or tool needs logic the service lacks, add it to the service.
4. `python -m ruff check . && python -m pytest -q tests`.

## Parity check

Any new service capability exposed on one surface: grep the other surface
(`web/app.py`, `mcp/tools.py`) and either expose it or note the gap in the issue. Never let one
surface enforce a rule the other skips.
