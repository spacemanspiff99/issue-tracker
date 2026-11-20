---
name: local-uat-preflight
description: Run the local manual-UAT readiness gate in an isolated Docker Compose project without disturbing the live dev app. Use before claiming local UAT readiness, before a UAT deploy, or when asked to run the full local test gate or browser UAT.
---

# Local UAT Preflight

Source of truth: `documentation/guides/deployment.md` (Local Docker Preflight Isolation), `documentation/guides/manual-uat.md`, and `documentation/guides/local-development.md`.

Every compose command uses this literal isolated prefix, written out in full each time (`<PF>` below). Shell variables do not persist between Bash calls, and the guard hook only allows `down -v` when the literal project name is in the command:

```text
<PF> = COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml
```

## 1. Capacity and live-dev baseline

```bash
df -h / /tmp
docker system df
curl -fsS http://192.168.10.20:8000/health   # live dev; record result, do not restart it
```

Low disk: stop and report. Do not prune volumes.

## 2. Gate (all must pass, or be listed as blockers)

```bash
<PF> config >/dev/null
<PF> build
<PF> run --rm app alembic upgrade head
<PF> run --rm app python -m pytest tests/
<PF> run --rm app ruff check src tests
<PF> run --rm app python -m issue_tracker.mcp.server --smoke
<PF> up -d app && curl -fsS http://localhost:18000/health
```

Then run the browser path inside the container (Playwright is in the image; never install it on the host): setup/login -> project -> issue -> dependency -> sprint -> close. A page counts as passing only if it is **styled and usable**. No JS errors alone is not enough. Save screenshots under `exports/` (gitignored).

## 3. Cleanup (disposable project only)

```bash
<PF> down -v
docker image rm issue_tracker_preflight-app
docker builder prune
docker system df
curl -fsS http://192.168.10.20:8000/health   # live dev must still be healthy
```

`down -v` is allowed **only** with `COMPOSE_PROJECT_NAME=issue_tracker_preflight`; the guard hook enforces this. Never run `up`, `down`, or `rm` against the default dev project unless the user asks to restart dev.

## 4. Report

Write pass/fail per check to a note from `documentation/uat/TEMPLATE-local-uat.md`, link it from the sprint, and update tracker evidence. On failure, debug from logs, request/response bodies, and DB state before changing code.
