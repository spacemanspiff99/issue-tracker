# Sprint 0168 Dev Preflight Evidence

Date: 2026-05-26

Sprint: `0168` Overnight dev finish, manual UAT, UAT deploy, and comprehensive validation

Scope: local dev readiness before source-control closeout and UAT deployment.

## Result

Pass for local dev preflight.

The current checkout passed a fresh isolated Docker build, empty PostgreSQL migration, full test suite, health check, MCP smoke, browser UAT, ruff, and compile check. The disposable preflight app, database volume, and image were removed after evidence was captured.

## Capacity Recovery

Initial host state before cleanup:

```text
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda2        32G   29G  1.1G  97% /
/dev/sda2        32G   29G  1.1G  97% /

Images          26        4         17.43GB   15.51GB (88%)
Build Cache     147       0         15.21GB   15.21GB
```

Cleanup performed:

- Removed obsolete isolated test images from previous `issue_tracker_browser_*` and `issue_tracker_empty_*` preflight projects.
- Ran `docker builder prune -f`.
- Did not remove live dev containers or tracker data volumes.

Post-cleanup state:

```text
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda2        32G   15G   16G  48% /
/dev/sda2        32G   15G   16G  48% /
```

Final post-preflight cleanup state:

```text
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda2        32G   16G   15G  52% /
/dev/sda2        32G   16G   15G  52% /

Images          6         4         3.567GB   1.529GB (42%)
Containers      4         2         288kB     267kB (92%)
Local Volumes   1         1         66.95MB   0B (0%)
Build Cache     33        0         0B        0B
```

Live containers left running:

```text
deployment-app-1 deployment-app Up 32 hours
issue-tracker-postgres postgres:16-alpine Up 3 days (healthy)
```

## Gates

Compose config:

```bash
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml config
```

Result: passed.

Fresh isolated Docker build:

```bash
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml build
```

Result: passed. The Playwright Chromium runtime dependency layer ran inside the Docker image path and was cached on retry; no host-level Playwright dependency install was run.

Empty database migration:

```bash
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml run --rm app alembic upgrade head
```

Result: passed through:

```text
0001_initial
0002_guidance_sync
0003_guidance_audit_events
0004_cancelled_issue_status
```

Full tests:

```bash
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/
```

Result:

```text
52 passed, 1 skipped, 1 warning in 13.77s
```

Health:

```bash
curl -fsS http://localhost:18000/health
```

Result:

```json
{"ok":true,"database":"ok"}
```

MCP smoke:

```bash
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml run --rm app python -m issue_tracker.mcp.server --smoke
```

Result: passed with expected tool list including `project.list`, `issue.create`, `issue.search`, `sprint.create`, `guidance_sync.health`, `backup.health`, `rule.resolve`, and `prompt.lint`.

Browser UAT:

```bash
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml run --rm -e RUN_BROWSER_UAT=1 -e UAT_BASE_URL=http://issue_tracker_preflight-app-1:8000 app python -m pytest tests/e2e/test_browser_uat.py
```

Result:

```text
1 passed, 1 warning in 23.31s
```

Ruff:

```bash
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml run --rm app python -m ruff check --no-cache .
```

Result:

```text
All checks passed!
```

Compile:

```bash
python3 -m compileall src/issue_tracker
```

Result: passed.

## Cleanup

Commands:

```bash
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml down -v
docker image rm issue_tracker_preflight-app
docker builder prune -f
```

Result: disposable preflight app, PostgreSQL container, preflight volume, preflight network, preflight image, and unused build cache removed.

## Remaining Work

- Review dirty worktree and prepare a dev-ready commit.
- Push exact SHA.
- Run UAT deploy source-of-truth gate before workflow dispatch.
- Run comprehensive UAT against the deployed SHA.
