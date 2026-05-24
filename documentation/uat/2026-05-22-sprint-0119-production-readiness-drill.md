# Sprint 0119 Production Readiness Drill

Date: 2026-05-22

Sprint: `0119` Production readiness comprehensive test drill

Source plan: `documentation/sprints/0119-production-readiness-comprehensive-test-drill.md`

## Summary

Result: blocked at `0122` migration safety.

Completed:

- `0120` Tracker reconciliation passed. Active tracker database was confirmed on existing Docker volume `deployment_issue_tracker_pgdata` through `http://127.0.0.1:8000/health`.
- Sprint `0112` was closed in the tracker with Sprint 0112 markdown and UAT evidence.
- Sprint `0119` and issues `0120` through `0128` were created and assigned in the tracker.
- Intake search was rerun for `To process`, `voice-feedback`, `audio`, `intake`, and `clarify`. Voice/audio/intake backlog matches were already `done`; remaining `audio` or `intake` hits were Sprint 0112 evidence/navigation records.
- `0121` Phase 1 gates passed in isolated Compose project `issue_tracker_preflight`.

Blocked:

- `0122` requires a restored production-like staging database. No production dump or staging database target is available in the local repo, `backups/`, or `exports/`.

## Evidence

Tracker health:

```bash
curl -fsS http://127.0.0.1:8000/health
```

Result:

```json
{"ok":true,"database":"ok"}
```

Phase 1:

```bash
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml config
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml build
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/unit/
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/integration/
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml run --rm app python -m issue_tracker.mcp.server --smoke
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml run --rm app python -m ruff check --no-cache .
```

Results:

- Compose config passed.
- Build passed.
- Unit tests: `26 passed`, with one pytest cache permission warning inside `/app`.
- Integration tests: `21 passed`, with one pytest cache permission warning inside `/app`.
- MCP smoke passed and listed compact project, issue, sprint, category, Guidance Sync, backup, rule, prompt, and sync tools.
- Ruff passed.
- Default tracker health remained `{"ok":true,"database":"ok"}` after preflight.

Phase 2 local migration checks:

```bash
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml run --rm app alembic upgrade head
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml exec postgres createdb -U issue_tracker issue_tracker_empty_test
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml run --rm -e DATABASE_URL=postgresql+psycopg://issue_tracker:issue_tracker@postgres:5432/issue_tracker_empty_test app alembic upgrade head
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml exec postgres dropdb -U issue_tracker issue_tracker_empty_test
```

Results:

- Disposable preflight database migration passed through `0001_initial`, `0002_guidance_sync`, and `0003_guidance_audit_events`.
- Empty test database migration passed through `0001_initial`, `0002_guidance_sync`, and `0003_guidance_audit_events`.
- Temporary empty test database was dropped after verification.

## STOP

Owner action required: provide a production dump and a separate staging PostgreSQL target, with outbound write credentials disabled, so `0122` can complete the production-like staging migration check.

Sprint `0119` remains open. Production-project readiness is not approved.
