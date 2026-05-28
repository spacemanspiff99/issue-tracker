# Local UAT Notes: Sprint 0043 Route And Runtime Slice

Date: 2026-05-15
Tester: Codex
Commit SHA: 198a534
Branch: main
Browser: not run
Environment: Docker Compose local app and PostgreSQL

## Runtime Gate

| Check | Command or step | Pass/Fail | Evidence | Blocker or notes |
|---|---|---|---|---|
| Compose config | `docker compose -f deployment/docker-compose.local.yml config` | Pass | Rendered app, postgres, volumes, network, and env configuration. | Added local `exports/` and `backups/` mounts. |
| Build | `docker compose -f deployment/docker-compose.local.yml build` | Pass | Image `deployment-app` built. | None. |
| Migration | `docker compose -f deployment/docker-compose.local.yml run --rm app alembic upgrade head` | Pass | Alembic used `PostgresqlImpl` and completed. | None. |
| Tests | `docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/` | Pass | `18 passed`. | Non-blocking pytest cache permission warning. |
| MCP smoke | `docker compose -f deployment/docker-compose.local.yml run --rm app python -m issue_tracker.mcp.server --smoke` | Pass | Returned expected tool list. | None. |
| Health | `curl -fsS http://localhost:8000/health` | Pass | `{"ok":true,"database":"ok"}`. | None. |

## Web UAT

| Step | Expected result | Pass/Fail | Evidence | Blocker or notes |
|---|---|---|---|---|
| Route coverage | Setup/login, project, category, issue, dependency, sprint, close, and issue-log paths are covered. | Pass | `tests/integration/test_web_routes.py` passed. | Route-level only. |
| Styling sanity | Key templates use centralized shell, spacing, forms, tables, badges, errors, and empty states. | Partial | Route tests render templates successfully. | Browser viewport walkthrough not run. |
| Close metadata | Originating LLM, closed by, and close note are visible after close. | Pass | Route test asserts issue detail close metadata. | None. |
| Dependency workflow | Dependency titles/display IDs are visible; cycle errors stay on issue page. | Pass | Route test asserts human-readable dependency context and cycle error. | None. |
| Sprint assignment | Assigned issue shows `in-progress` issue status. | Pass | Route test asserts sprint page status. | None. |

## MCP UAT

| Check | Command or step | Pass/Fail | Evidence | Blocker or notes |
|---|---|---|---|---|
| MCP smoke | `python -m issue_tracker.mcp.server --smoke` | Pass | Smoke returned `project.list`, issue tools, sprint tools, `category.list`, and `next_action`. | None. |
| Compact output | `python -m pytest tests/integration/test_mcp_tools.py` | Pass | MCP tests cover compact issue output, full detail opt-in, dependency, sprint, category, and next action paths. | None. |

## Import Export UAT

| Check | Command or step | Pass/Fail | Evidence | Blocker or notes |
|---|---|---|---|---|
| Export JSON | `issue-tracker export-json 1 exports/manual-uat-project.json` | Pass | Command completed after Compose mount fix. | Generated file is ignored. |
| Import JSON | `issue-tracker import-json exports/manual-uat-project.json Manual-UAT-Restored --category-map IT-1=IT-1` | Pass | Command returned project id `2`. | Local database now contains restored smoke project. |
| Secret safety | Export should contain no secrets or password hashes. | Pass | Export code only serializes project tracker data. | Full file not committed. |

## Findings

| Finding | Severity | Follow-up issue | Owner action | Status |
|---|---|---|---|---|
| Browser-level desktop/mobile UAT not run. | Medium | Sprint 0043 issue `0008` | Human or browser-capable agent should run `documentation/guides/manual-uat.md`. | Open |
| Sprint 0043 feature slices now have route/service coverage, but no visual viewport pass. | Medium | Sprint 0043 issue `0008` | Run a browser-capable desktop/mobile walkthrough and record results. | Open |

## Decision

Local runtime and route-level UAT for the modern UI and Sprint 0043 feature slices are ready with caveats.

Decision rationale: Docker runtime, migration, tests, MCP smoke, health, and import/export gates pass. Browser-level manual UAT is not complete.
