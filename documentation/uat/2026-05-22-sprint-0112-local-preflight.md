# Local Preflight Notes: Sprint 0112 UAT Candidate

Date: 2026-05-22
Candidate branch: `deploy/app-host-targets-0112`
Candidate SHA: `cf6257727ab908291aba1873c49167f39fc2cdfd`
Tester: Codex in isolated Docker Compose stacks

## Result

Local source freeze, upstream reconciliation, container tests, migration gates, MCP smoke, Ruff, and browser UAT passed.

## Evidence

Commands:

```bash
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml run --rm app python -m ruff check --no-cache .
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml run --rm app python -m issue_tracker.mcp.server --smoke
COMPOSE_PROJECT_NAME=issue_tracker_empty_0112 POSTGRES_CONTAINER_NAME=issue-tracker-empty-0112-postgres APP_HTTP_PORT=18001 docker compose -f deployment/docker-compose.local.yml run --rm app alembic upgrade head
COMPOSE_PROJECT_NAME=issue_tracker_browser_0112 POSTGRES_CONTAINER_NAME=issue-tracker-browser-0112-postgres APP_HTTP_PORT=18002 docker compose -f deployment/docker-compose.local.yml run --rm app alembic upgrade head
curl -fsS http://127.0.0.1:18002/health
COMPOSE_PROJECT_NAME=issue_tracker_browser_0112 POSTGRES_CONTAINER_NAME=issue-tracker-browser-0112-postgres APP_HTTP_PORT=18002 docker compose -f deployment/docker-compose.local.yml exec -e RUN_BROWSER_UAT=1 app python -m pytest tests/e2e/test_browser_uat.py
```

Observed results:

- Full test suite: 47 passed, 1 skipped.
- Ruff: all checks passed.
- MCP smoke: passed and listed project, issue, sprint, category, guidance sync, backup, rule, prompt, and sync tools.
- Empty database migration: ran `0001_initial`, `0002_guidance_sync`, and `0003_guidance_audit_events`.
- Browser UAT: 1 passed after fixing stale setup-page detection in the test.
- Isolated app health: `{"ok":true,"database":"ok"}`.

Ignored local artifacts:

- `exports/browser-uat-0078/*.png`
- temporary Compose project volumes and containers, removed after use.
