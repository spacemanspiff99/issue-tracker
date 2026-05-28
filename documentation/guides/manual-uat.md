# Manual UAT Guide

Use this guide after the Docker runtime gate passes in `documentation/issues/0008-local-runtime-gate.md`.

## Preconditions

- The current user can run Docker without `sudo`.
- Compose config validates.
- The app image builds from the current checkout.
- Migrations have been run explicitly.
- Tests pass through the app service.
- The local stack is running at `http://localhost:8000`.
- The host has enough free disk for a fresh image build and Playwright/browser layers.

Commands:

```bash
df -h / /tmp
docker system df
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml config
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml build
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml run --rm app alembic upgrade head
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/
docker compose -f deployment/docker-compose.local.yml up
```

Use the isolated `COMPOSE_PROJECT_NAME`, `POSTGRES_CONTAINER_NAME`, and `APP_HTTP_PORT` values for temporary-worktree preflight on the dev host. Check `http://192.168.10.20:8000/health` before and after the preflight so the live dev app is not disrupted. Use the default `docker compose ... up` command only when intentionally running or restarting the normal local stack.

Run Playwright and browser UAT inside the Docker image or app container. The image installs Chromium and its Linux runtime dependencies during the Docker build; do not run host-level `playwright install --with-deps` or install browser system packages on the dev host from an agent session.

Cleanup after isolated preflight:

```bash
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml down -v
docker image rm issue_tracker_preflight-app
docker builder prune
docker system df
```

Only run `down -v` against the isolated preflight project named above. Do not remove the default dev project, its containers, or any Docker volume that may contain tracker data unless that exact target has been explicitly confirmed. If disk is still tight, prefer naming and removing obsolete preflight images before considering broader Docker cleanup.

Health check:

```bash
curl -fsS http://localhost:8000/health
```

Expected result:

```json
{"ok":true,"database":"ok"}
```

## Browser Sanity

For every page below, verify:

- The page is visibly styled, not raw unstyled HTML.
- Text fits within controls and tables.
- Forms are usable with keyboard and mouse.
- Navigation links return to the expected parent page.
- No secret values are shown in the page.

Record results in `documentation/uat/YYYY-MM-DD-local-uat.md`.

## UAT Path

### 1. First-Run Setup

Open `http://localhost:8000/setup`.

Steps:

1. Enter username `admin`.
2. Enter a local-only test password.
3. Submit the form.

Expected:

- Admin user is created.
- Browser redirects to the project list.
- Session cookie is HTTP-only and SameSite=Lax.
- Password is not shown or logged.

### 2. Login And Logout

Steps:

1. Use the logout button.
2. Open `http://localhost:8000/login`.
3. Log in with the admin credentials.

Expected:

- Invalid credentials show inline validation.
- Valid credentials return to the project list.
- Repeated failed attempts eventually show rate limiting.

### 3. Project Creation

Steps:

1. On the project list, create project `Manual UAT Project`.
2. Leave repo URL blank or use `https://github.com/spacemanspiff99/issue-tracker`.

Expected:

- Browser redirects to the project detail page.
- Project is listed on the project list page.

### 4. Category Creation

Steps:

1. On the project detail page, create category key `IT-1`.
2. Use name `Tracker State Integrity`.
3. Use checklist `Verify sequence allocation, status transitions, dependencies, and close metadata.`

Expected:

- Category appears in the category list.
- Category is available in the issue creation form.
- No peer project taxonomy is required.

### 5. Required Acceptance Criteria Validation

Steps:

1. Try to create issue `Missing AC UAT` with an empty acceptance criteria field.

Expected:

- Page shows inline validation: acceptance criteria are required.
- No new issue row is created.
- Existing project context remains visible.

### 6. Issue Creation

Steps:

1. Create issue `Prepare blocker`.
2. Select category `IT-1`.
3. Use acceptance criteria `- [ ] Blocker issue can be linked`.
4. Create issue `Complete blocked work`.
5. Use acceptance criteria `- [ ] Blocked issue can be closed`.

Expected:

- Issues are visible on the project detail page.
- Display IDs use the shared four-digit sequence convention, such as `0001` and `0002`.
- Both issues start in backlog.

### 7. Dependency Creation

Steps:

1. Open the `Complete blocked work` issue detail page.
2. Add `Prepare blocker` as the blocker issue.

Expected:

- Dependency is listed on the issue detail page.
- Self-dependency and cycle attempts are rejected if tried.

### 8. Sprint Creation And Assignment

Steps:

1. Return to the project detail page.
2. Create sprint `Local manual UAT sprint`.
3. On the sprint detail page, add `Complete blocked work`.

Expected:

- Sprint display ID continues the same project-local sequence used by issues.
- Added issue appears on the sprint page.
- Added issue status changes to `in-progress`.

### 9. Issue Close

Steps:

1. Open `Complete blocked work`.
2. Close it with originating LLM `gpt-5.5`.
3. Add close note `Manual UAT close path verified`.

Expected:

- Issue status changes to `done`.
- Close metadata is preserved.
- Attempting to reopen a closed issue is rejected by service tests.

### 10. Issue Log View

Steps:

1. Return to the project detail page.
2. Review the issue log section.

Expected:

- Issue log section is visible.
- Empty state is understandable if no recurring issue entries exist yet.

### 11. MCP Smoke

Run:

```bash
docker compose -f deployment/docker-compose.local.yml run --rm app python -m issue_tracker.mcp.server --smoke
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/integration/test_mcp_tools.py
```

Expected:

- Smoke command returns the expected tool list.
- MCP compact-output tests pass.

### 12. Import Export Smoke

Run:

```bash
docker compose -f deployment/docker-compose.local.yml run --rm app issue-tracker export-json 1 exports/manual-uat-project.json
docker compose -f deployment/docker-compose.local.yml run --rm app issue-tracker import-json exports/manual-uat-project.json Manual-UAT-Restored --category-map IT-1=IT-1
```

Expected:

- Export contains no secrets, sessions, password hashes, or environment values.
- Import requires explicit category mapping and creates a restored project.
- Generated export remains ignored by git.

## Local Reset

Local reset is destructive and only for the local development database:

```bash
docker compose -f deployment/docker-compose.local.yml down
docker volume rm deployment_issue_tracker_pgdata
docker compose -f deployment/docker-compose.local.yml run --rm app alembic upgrade head
```

Do not use local reset commands against external or production PostgreSQL.
