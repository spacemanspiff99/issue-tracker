# Sprint 0043: Overnight Modern Web App Buildout

Status: active; blocked on browser-capable manual UAT for issue `0008`
Tracker goal: Overnight modern web app buildout
Tracker context: Oversized dogfood sprint loaded for overnight autonomous work. Work high-priority items first, keep Docker verification gates, and leave STOP notes for unfinished slices.
Recommended model: GPT-5.5 medium for UI implementation; GPT-5.5 high for runtime, auth, schema, MCP, and closeout gates.

## Scope Executed

This pass completed the first high-priority slice of Sprint 0043:

- Modern app shell, centralized styling, responsive layout, consistent forms, tables, badges, errors, and empty states.
- Project dashboard improvements with repo and default branch context.
- Project detail improvements for issue/category/sprint/log work areas, validation context preservation, category display, and sprint list visibility.
- Issue detail improvements for metadata, acceptance criteria, dependency context, close metadata, and inline dependency errors.
- Sprint detail improvements for prompt/context display, assignment controls, issue status visibility, and inline duplicate assignment errors.
- Service and MCP parity hardening for category validation, closed sprint mutation rejection, close metadata detail, compact MCP outputs, and mutation next-step hints.
- Local Compose export/import path fixed by mounting ignored `exports/` and `backups/` folders.

The continuation pass implemented the remaining route/service feature slices except browser-only UAT:

- Saved issue views for all, backlog, active sprint, blocked, done, and uncategorized work.
- Project search, project/backlog/board navigation, and server-rendered backlog ordering controls.
- Project and sprint progress summaries, dependency health indicators, and activity feed.
- Issue edit forms, inline status/priority controls, quick create, planning metadata, comments, and GitHub references.
- Project-scoped recommended tracker taxonomy, story grouping, delivery phase, milestones, custom fields, story templates, and sprint/story rollups using existing service-managed fields.
- Planning mirror and markdown import guidance, plus backup/restore command UX around existing JSON import/export.
- MCP issue search parity for saved views without expanding compact default outputs.
- Modernization decision documentation in `documentation/guides/web-ui-modernization.md`.

## Verification Evidence

Commands run on 2026-05-15:

```bash
docker compose -f deployment/docker-compose.local.yml config
docker compose -f deployment/docker-compose.local.yml build
docker compose -f deployment/docker-compose.local.yml run --rm app alembic upgrade head
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/
docker compose -f deployment/docker-compose.local.yml run --rm app python -m issue_tracker.mcp.server --smoke
docker compose -f deployment/docker-compose.local.yml up -d
curl -fsS http://localhost:8000/health
docker compose -f deployment/docker-compose.local.yml run --rm app issue-tracker export-json 1 exports/manual-uat-project.json
docker compose -f deployment/docker-compose.local.yml run --rm app issue-tracker import-json exports/manual-uat-project.json Manual-UAT-Restored --category-map IT-1=IT-1
```

Results:

- Compose config: passed after adding local export and backup mounts.
- Build: passed.
- Migration: passed.
- Full pytest: passed with `18 passed`; pytest emitted a non-blocking cache permission warning under `/app/.pytest_cache`.
- MCP smoke: passed and returned the expected tool list.
- Health: passed with `{"ok":true,"database":"ok"}`.
- Import/export smoke: passed after the Compose mount fix; generated export stayed under ignored `exports/`.

Additional commands run on 2026-05-15:

```bash
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/
docker compose -f deployment/docker-compose.local.yml run --rm app python -m ruff check --no-cache .
```

Results:

- Full pytest: passed with `23 passed`; pytest emitted the existing non-blocking cache permission warning under `/app/.pytest_cache`.
- Ruff: passed.

## Caveats

- Browser-level manual UAT with desktop and mobile viewport notes has not been completed. `which chromium`, `which google-chrome`, and `which firefox` all returned not found in this environment. Route-level tests prove rendered HTML and behavior, but issue `0008` remains open until a browser-capable walkthrough records styling and usability evidence.
- Drag-and-drop backlog ordering is represented by draggable board cards plus a route-tested ordering endpoint and server-rendered order form. A richer JavaScript drag/drop layer remains a possible future enhancement, but the ordering behavior is implemented without a frontend framework.
- The running tracker database is local state. This markdown file is the durable handoff for the implemented slice and remaining STOP work.

## Finish-The-Sprint Plan

The implementation slices are complete except browser-only issue `0008`. A browser-capable session should run `documentation/guides/manual-uat.md`, record desktop and mobile notes, close `0008`, rerun the final verification gate, and then close Sprint 0043.

## Backlog Additions Requested 2026-05-15

The following project backlog issues were added after the Sprint 0043 feature pass:

- `0045` Polish drag-and-drop issue ordering across backlog and board.
- `0046` Add release planning across multiple sprints.
- `0047` Add issue sidebar for fast issue visibility and navigation.
- `0048` Add voice feedback intake for audio bug reports and feature requests.

Project category `CLARIFY` was added as `Not Done / Needs Clarifications` for incomplete intake items that need follow-up before implementation.

The original provider-specific idea for Google Speech-to-Text plus Sonnet 4.6 was intentionally discarded. Issue `0048` now focuses on audio feedback intake and a Codex processing workflow that can turn recorded bug reports or feature requests into investigated, build-ready backlog issues using approved available tooling.

Remaining issue:

1. Browser UAT gate: `0008`.

## STOP

Sprint 0043 is blocked on issue `0008`.

Blocker: this execution environment has no browser binary available for desktop/mobile viewport inspection.

Owner action: install or provide a browser-capable UAT environment, then run `documentation/guides/manual-uat.md` and record results under `documentation/uat/`.

Retry command:

```bash
which chromium || which google-chrome || which firefox
docker compose -f deployment/docker-compose.local.yml up -d
curl -fsS http://localhost:8000/health
```
