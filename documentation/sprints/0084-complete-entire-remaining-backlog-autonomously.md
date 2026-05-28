# Sprint 0084: Complete Entire Remaining Backlog Autonomously

Status: complete in the local tracker

Tracker sprint: `0084` Complete entire remaining backlog autonomously

Origin: weekend autonomous execution request on 2026-05-16.

## Intent

Complete every remaining issue in the `issue-tracker` backlog in one autonomous sprint. Do not reinterpret this sprint as permission to finish only one phase or a convenient slice.

The sprint may stop only when one of these is true:

- every assigned issue is implemented, verified, closed with evidence, and the sprint is closed;
- a specific owner action blocks remaining work, the blocker is recorded on the affected issue(s), and all unblocked work has still been completed;
- the user explicitly accepts named deferrals.

## Intake Check

Backlog planning included the required voice/audio intake check.

- `0082` was transcribed from `exports/voice-feedback/1/87097df7b0aa4720a46aaa46bddb657d.webm` and converted into issue-log automation work.
- `0083` was transcribed from `exports/voice-feedback/1/e66918ca37e3405d9503798aa769e2ad.webm`, merged into `0081`, and closed as captured to avoid duplicate sprint work.
- Temporary Google Cloud Storage transcription uploads under `speech-intake/` were deleted after transcript generation. The bucket lifecycle fallback deletes future `speech-intake/` objects after 1 day.

## Model And Reasoning

Recommended model/reasoning: GPT-5.5 `high`.

Use `high` throughout this sprint because it combines schema/migration work, auth-safe repository scanning, MCP contracts, GitHub integration, UI changes, browser UAT, and long autonomous closeout. Use `medium` only for tightly bounded template/CSS edits after the service contracts are already tested.

## Scope

| Order | Tracker ID | Phase | Category | Priority | Issue |
|---:|---|---|---|---|---|
| 1 | `0081` | Phase 1 - urgent voice intake UX | `WEB-3` | urgent | Autosave voice intake recordings with delete, restart, and continue controls |
| 2 | `0080` | Phase 1 - urgent overview dashboard | `PROD-1` | urgent | Add overview dashboard lifecycle and blocked-reason rollups |
| 3 | `0082` | Phase 1 - issue-log analysis | `PROD-3` | high | Add issue log automation for failed agent completion and recurring bugs |
| 4 | `0056` | Phase 2 - guidance sync schema | `IT-3` | high | Model guidance sources, targets, branches, snapshots, and drift |
| 5 | `0057` | Phase 2 - repository inventory scanning | `IT-5` | high | Add repository inventory and auth-safe scanning |
| 6 | `0058` | Phase 2 - drift detection | `PROD-4` | high | Build branch-aware drift detection service |
| 7 | `0060` | Phase 3 - sync proposals | `PROD-2` | high | Create sync proposal workflow |
| 8 | `0061` | Phase 3 - PR execution | `PROD-4` | high | Add PR-based sync execution |
| 9 | `0062` | Phase 3 - ingestion | `PROD-4` | high | Add GitHub webhook or polling ingestion |
| 10 | `0063` | Phase 3 - audit and rollback | `IT-1` | high | Add sync audit log and rollback planning |
| 11 | `0059` | Phase 4 - dashboard UI | `PROD-1` | normal | Add Guidance Sync dashboard |
| 12 | `0064` | Phase 4 - MCP tools | `IT-4` | high | Add MCP tools for guidance sync |
| 13 | `0065` | Phase 4 - containerized UAT | `WEB-4` | high | Add containerized UAT for rule sync workflows |

## Dependency-Aware Execution Plan

1. Finish urgent local dogfood UX first: `0081`, `0080`, and `0082`.
2. Build the read-only Guidance Sync foundation next: `0056`, `0057`, and `0058`.
3. Add proposal, execution, ingestion, and audit workflows after the drift model is stable: `0060`, `0061`, `0062`, and `0063`.
4. Add dashboard, MCP tools, and end-to-end UAT last: `0059`, `0064`, and `0065`.
5. Close each tracker issue only after its own acceptance criteria pass. Keep Sprint `0084` active until all assigned issues are done or explicitly blocked/deferred.

## Verification Gates

Run the smallest relevant gate after each issue, then run the full gate before sprint close.

Required final commands:

```bash
docker compose -f deployment/docker-compose.local.yml exec app python -m ruff check --no-cache .
docker compose -f deployment/docker-compose.local.yml exec app python -m pytest tests/
docker compose -f deployment/docker-compose.local.yml exec app alembic upgrade head
curl -fsS http://127.0.0.1:8000/health
docker compose -f deployment/docker-compose.local.yml exec -e RUN_BROWSER_UAT=1 app python -m pytest tests/e2e/test_browser_uat.py
```

Schema changes require a fresh empty-database migration check before closing schema-related work.

UI-facing work requires route-level or browser evidence for desktop and mobile usability.

MCP work requires compact-output smoke tests and token-discipline coverage.

Auth and GitHub/GCS behavior must not log secrets, tokens, raw audio bytes, private payloads, database dumps, backups, or generated exports.

## Close Evidence Required

Completed on 2026-05-16.

Tracker closeout:

- Sprint `0084` is closed.
- All assigned issues are `done`: `0081`, `0080`, `0082`, `0056`, `0057`, `0058`, `0060`, `0061`, `0062`, `0063`, `0059`, `0064`, and `0065`.
- No open issues remain in the active `issue-tracker` project.

Changed implementation surfaces:

- Voice intake autosave/delete/start-over/continue controls: `src/issue_tracker/web/templates/intake.html`, `src/issue_tracker/web/app.py`, `src/issue_tracker/services/tracker.py`.
- Overview lifecycle and blocked-reason rollups: `src/issue_tracker/services/tracker.py`, `src/issue_tracker/web/templates/project_detail.html`.
- Issue-log automation and issue-detail visibility: `src/issue_tracker/services/tracker.py`, `src/issue_tracker/web/templates/issue_detail.html`.
- Guidance Sync schema and services: `src/issue_tracker/domain/models.py`, `src/issue_tracker/services/guidance_sync.py`, `migrations/versions/0002_guidance_sync.py`, `migrations/versions/0003_guidance_audit_events.py`.
- Guidance Sync UI and MCP: `src/issue_tracker/web/templates/guidance_sync.html`, `src/issue_tracker/web/app.py`, `src/issue_tracker/mcp/tools.py`, `src/issue_tracker/mcp/server.py`.
- Verification coverage: `tests/unit/test_services.py`, `tests/unit/test_guidance_sync.py`, `tests/integration/test_web_routes.py`, `tests/integration/test_mcp_tools.py`, `tests/e2e/test_browser_uat.py`.

Verification commands:

```bash
docker compose -f deployment/docker-compose.local.yml exec app python -m ruff check --no-cache .
docker compose -f deployment/docker-compose.local.yml exec app python -m pytest tests/
docker compose -f deployment/docker-compose.local.yml exec -e RUN_BROWSER_UAT=1 app python -m pytest tests/e2e/test_browser_uat.py
docker compose -f deployment/docker-compose.local.yml exec app alembic upgrade head
docker compose -f deployment/docker-compose.local.yml exec postgres createdb -U issue_tracker issue_tracker_empty_gate
docker compose -f deployment/docker-compose.local.yml exec -e DATABASE_URL=postgresql+psycopg://issue_tracker:issue_tracker@postgres:5432/issue_tracker_empty_gate app alembic upgrade head
docker compose -f deployment/docker-compose.local.yml exec postgres dropdb -U issue_tracker issue_tracker_empty_gate
curl -fsS http://127.0.0.1:8000/health
docker compose -f deployment/docker-compose.local.yml exec app python -m issue_tracker.mcp.server --smoke
```

Results:

- Ruff: all checks passed.
- Full pytest: 36 passed, 1 skipped. The skipped test is the opt-in browser UAT guard.
- Explicit browser UAT: 1 passed, including Guidance Sync desktop/mobile route checks and voice recording autosave.
- Running database migration: upgraded through `0003_guidance_audit_events`.
- Empty PostgreSQL database migration: upgraded from base through `0001_initial`, `0002_guidance_sync`, and `0003_guidance_audit_events`.
- `/health`: `{"ok":true,"database":"ok"}`.
- MCP smoke: includes `guidance_sync.health`, `guidance_sync.drift_list`, and `guidance_sync.create_proposal`.
- No owner blockers or accepted deferrals remain.

## STOP

Sprint `0084` is complete and closed. The entire previously open backlog is closed with evidence.
