# Local Manual UAT Notes

Date:
Tester:
Commit SHA:
Branch:
Browser:
Environment:

## Runtime Gate

| Check | Command or step | Pass/Fail | Evidence | Blocker or notes |
|---|---|---|---|---|
| Compose config | `docker compose -f deployment/docker-compose.local.yml config` |  |  |  |
| Build | `docker compose -f deployment/docker-compose.local.yml build` |  |  |  |
| Migration | `docker compose -f deployment/docker-compose.local.yml run --rm app alembic upgrade head` |  |  |  |
| Tests | `docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/` |  |  |  |
| Health | `curl -fsS http://localhost:8000/health` |  |  |  |

## Web UAT

| Step | Expected result | Pass/Fail | Evidence | Blocker or notes |
|---|---|---|---|---|
| First-run setup | Admin user is created; password not exposed. |  |  |  |
| Login/logout | Valid login works; invalid login shows inline error. |  |  |  |
| Project creation | Project appears and opens. |  |  |  |
| Category creation | Category is project-scoped and selectable. |  |  |  |
| Missing AC validation | Inline error appears; no issue row is created. |  |  |  |
| Issue creation | Issues receive four-digit display IDs. |  |  |  |
| Dependency creation | Blocker edge appears; invalid cycles are rejected by tests. |  |  |  |
| Sprint creation | Sprint receives shared sequence ID. |  |  |  |
| Sprint issue assignment | Issue appears in sprint and moves to in-progress. |  |  |  |
| Issue close | Done status and originating LLM metadata are preserved. |  |  |  |
| Issue log view | Issue log section is visible. |  |  |  |
| Styling sanity | Pages are visibly styled and usable. |  |  |  |

## MCP UAT

| Check | Command or step | Pass/Fail | Evidence | Blocker or notes |
|---|---|---|---|---|
| MCP smoke | `python -m issue_tracker.mcp.server --smoke` |  |  |  |
| Compact output | `python -m pytest tests/integration/test_mcp_tools.py` |  |  |  |

## Import Export UAT

| Check | Command or step | Pass/Fail | Evidence | Blocker or notes |
|---|---|---|---|---|
| Export JSON | `issue-tracker export-json 1 exports/manual-uat-project.json` |  |  |  |
| Import JSON | `issue-tracker import-json ... --category-map IT-1=IT-1` |  |  |  |
| Secret safety | Export contains no secrets or password hashes. |  |  |  |

## Findings

| Finding | Severity | Follow-up issue | Owner action | Status |
|---|---|---|---|---|
|  |  |  |  |  |

## Decision

Choose one:

- Local manual UAT ready.
- Local manual UAT ready with caveats.
- Local manual UAT not ready.

Decision rationale:
