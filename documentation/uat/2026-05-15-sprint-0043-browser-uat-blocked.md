# Local UAT Notes: Sprint 0043 Browser UAT Blocked

Date: 2026-05-15
Tester: Codex
Branch: main
Browser: blocked; no Chromium, Chrome, or Firefox binary is installed in the execution environment.
Environment: Docker Compose local app and PostgreSQL

## Browser Tooling Check

| Check | Command | Result |
|---|---|---|
| Chromium | `which chromium` | Not found |
| Chrome | `which google-chrome` | Not found |
| Firefox | `which firefox` | Not found |

## Desktop And Mobile Viewport Evidence

| Viewport | Pass/Fail | Evidence | Blocker |
|---|---|---|---|
| Desktop | Blocked | Browser binary unavailable. Route tests render the relevant pages, but no visual viewport inspection was possible. | Install or provide a browser automation tool, then run `documentation/guides/manual-uat.md`. |
| Mobile | Blocked | Browser binary unavailable. Route tests render the relevant pages, but no visual viewport inspection was possible. | Install or provide a browser automation tool, then run `documentation/guides/manual-uat.md`. |

## Route Coverage Completed Instead

The following browser-facing workflows have route-level tests:

- setup and login
- project list and project detail
- saved views and project search
- backlog and board navigation
- category creation and recommended taxonomy
- issue creation, inline status and priority update, edit form, planning metadata, comments, and GitHub references
- dependency creation and cycle validation
- sprint creation, assignment, detail rollups, and close metadata visibility
- planning and backup guidance pages

Command:

```bash
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/integration/test_web_routes.py
```

Result: passed as part of the full `tests/` gate with `23 passed`.

## Decision

Issue `0008` remains open. Sprint 0043 cannot be fully closed until a browser-capable run records desktop and mobile viewport notes for `documentation/guides/manual-uat.md`.
