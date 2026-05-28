# Sprint Plan: Overnight Dev Finish, Manual UAT, UAT Deploy, And Comprehensive Validation

Status: active tracker sprint, overnight execution started

Created: 2026-05-26

Parent plan: `documentation/sprints/0154-ai-coding-workflow-ux-reset-implementation-plan.md`

Tracker sprint: `0168`

Tracker issues: `0169` through `0175`

Recommended model/reasoning: GPT-5.5 `high`

Use high reasoning because the work touches Docker host capacity, local preflight evidence, source-of-truth deployment gates, UAT mutation safety, and comprehensive browser/manual validation.

## Goal

Finish local dev readiness, record manual UAT evidence, push an exact committed SHA to UAT, and run comprehensive UAT testing without losing tracker state or mutating UAT data unexpectedly.

This sprint is intentionally iterative for overnight execution. Each issue should be closed only after its evidence is recorded. If a remote mutation or destructive operation is needed, stop at the exact confirmation gate required by `AGENTS.md`.

## Current Baseline

- Local dev stack is running and `/health` returned `{"ok":true,"database":"ok"}` before this sprint was created.
- Full Docker test suite passed earlier in the session: `52 passed, 1 skipped`.
- Isolated browser UAT passed earlier in the session against `issue_tracker_browser_0154`.
- A fresh preflight image build later failed after building layers because the host filesystem reached 100% and Compose could not write build metadata.
- After removing the failed preflight image and builder cache, the host still reported only about 1.1G free on `/`.
- The worktree is dirty with both pre-existing changes and sprint changes. Do not revert unrelated user work.

## Issues

| Order | Tracker ID | Phase | Priority | Issue |
|---:|---|---|---|---|
| 1 | `0169` | A. Local recovery | urgent | Recover Docker capacity and keep preflight images clean |
| 2 | `0170` | B. Local preflight | urgent | Rerun fresh isolated local preflight gate |
| 3 | `0171` | C. Evidence and tracker closeout | urgent | Write dev manual UAT evidence and close verified local work |
| 4 | `0172` | D. Source control | urgent | Prepare dev-ready commit and push exact SHA |
| 5 | `0173` | E. UAT deploy | urgent | Dispatch UAT code deploy with source-of-truth gate |
| 6 | `0174` | F. UAT comprehensive test | urgent | Run comprehensive UAT test suite and manual workflow coverage |
| 7 | `0175` | G. Closeout | high | Finalize release evidence and STOP handoff |

## Execution Plan

### Phase A: Local Recovery

Purpose: recover enough disk for a fresh preflight build without touching tracker data volumes or live dev containers.

Commands:

```bash
df -h / /tmp
docker system df
docker image ls --format '{{.Repository}}:{{.Tag}} {{.ID}} {{.Size}}'
```

Allowed cleanup:

- Remove obsolete temporary/preflight images by exact image name or ID.
- Remove unused builder cache with `docker builder prune`.
- Recheck `df -h / /tmp` and `docker system df`.
- Keep Playwright browser dependency installation inside the Docker image or app container. Do not install Chromium libraries or Playwright system dependencies on the host.

STOP:

- Do not remove named Docker volumes, the live dev project containers, UAT containers, production containers, or broad Docker resources without explicit target confirmation.

### Phase B: Fresh Local Preflight

Purpose: prove current dev is ready from a fresh isolated Docker path.

Commands:

```bash
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml config
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml build
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml run --rm app alembic upgrade head
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml up -d app
curl -fsS http://localhost:18000/health
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml run --rm app python -m issue_tracker.mcp.server --smoke
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml run --rm -e RUN_BROWSER_UAT=1 -e UAT_BASE_URL=http://issue_tracker_preflight-app-1:8000 app python -m pytest tests/e2e/test_browser_uat.py
```

Cleanup:

```bash
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml down -v
docker image rm issue_tracker_preflight-app
docker builder prune
docker system df
```

### Phase C: Evidence And Tracker Closeout

Purpose: make the local readiness state recoverable.

Required outputs:

- `documentation/uat/2026-05-26-sprint-0168-dev-preflight.md`
- Updated evidence section in this sprint plan.
- Updated evidence or STOP handoff in the parent `0154` sprint plan.
- Tracker issue close metadata for only the issues that passed.

### Phase D: Source Control

Purpose: make UAT deployment source-of-truth clean.

Commands:

```bash
git status --short
git branch --show-current
git rev-parse HEAD
git diff --check
```

After reviewing intended files, stage and commit only the intended work. Push the branch and verify local and remote SHA match before any UAT workflow dispatch.

### Phase E: UAT Deploy

Purpose: deploy committed code to UAT while preserving UAT data by default.

Before dispatch, state:

- Branch.
- Exact commit SHA.
- Whether local and remote match.
- Workflow name and inputs, including `expected_deploy_sha`.
- Data policy: code deploy only; do not overwrite UAT data.
- Rollback outline.

STOP:

- Do not dispatch the UAT deploy workflow until the exact branch/SHA and data policy are recorded and the user has explicitly approved the remote code mutation if required by current guidance.
- Do not refresh, reset, restore, or overwrite UAT data unless the latest user response contains `CONFIRM OVERWRITE uat`.

### Phase F: Comprehensive UAT Test

Purpose: prove the deployed UAT app with the committed SHA.

Coverage:

- `/health` database check.
- Setup/login or existing-user access path.
- Intake recording success or actionable secure-context failure.
- Audio upload fallback.
- Manual quick intake to `Needs processing`.
- Processing into `Needs clarification` and `Ready for Codex`.
- Backlog workflow saved views.
- Overview command-center count drill-downs.
- Sprint Board route-backed movement.
- Durable cancel/archive and accidental draft discard.
- Closeout evidence.
- Backup and Guidance Sync pages.
- MCP smoke.
- Desktop and mobile usability.

Required output:

- `documentation/uat/2026-05-26-sprint-0168-uat-comprehensive.md`

### Phase G: Closeout

Purpose: leave a clean morning handoff.

Required closeout:

- Tracker issue statuses reflect real evidence.
- Sprint remains active only if an issue is blocked or awaiting confirmation.
- Final report names changed files, verification commands, blocked checks, deployed SHA if any, and remaining STOP handoff.

## Evidence Log

Add timestamped entries here as phases run.

- 2026-05-26: Created tracker sprint `0168` with issues `0169` through `0175`.
- 2026-05-26: Phase A passed. Recovered host disk from 97% used and 1.1G free to 48% used and 16G free by removing obsolete isolated preflight images and unused Docker build cache. Live dev containers and tracker data volume were preserved.
- 2026-05-26: Updated process guidance to clarify that Playwright browser dependencies are installed inside the Docker image or app container, never on the host from an agent session.
- 2026-05-26: Phase B passed. Fresh isolated preflight evidence is recorded in `documentation/uat/2026-05-26-sprint-0168-dev-preflight.md`: compose config, Docker build, empty DB migration, full tests, `/health`, MCP smoke, browser UAT, ruff, compile, and isolated cleanup all passed.
- 2026-05-26: Phase D passed for source-control publication. Committed and pushed the tested state to `origin/deploy/app-host-targets-0112`. Before UAT dispatch, re-read `git rev-parse HEAD` and `git ls-remote origin refs/heads/deploy/app-host-targets-0112`; use only the exact matching SHA as `expected_deploy_sha`. Note: `origin/dev` was observed at `836a1be69eef07b31f223fee9229507899e842c9`; the tested/pushed UAT candidate is the deployment branch, not the current `dev` branch head.

## UAT Deploy Gate

Prepared operation:

- Workflow: `.github/workflows/local-pipeline.yml` (`App Deploy Pipeline`; listed by `gh workflow list` as `Local Dev UAT Pipeline`).
- Ref: `deploy/app-host-targets-0112`.
- Expected deploy SHA: use the exact final `git rev-parse HEAD` value after all source-control commits are complete and after confirming the remote ref matches.
- Target: UAT host `192.168.10.26`, deploy path `/home/akun/issue-tracker`, user `akun`.
- Production deploy: `false`.
- Data policy: code deploy only; preserve existing UAT database by default. Do not overwrite, restore, reset, or refresh UAT data.

Dispatch command when explicitly approved:

```bash
gh workflow run local-pipeline.yml \
  --ref deploy/app-host-targets-0112 \
  -f uat_host=192.168.10.26 \
  -f prod_host=192.168.10.27 \
  -f deploy_user=akun \
  -f deploy_path=/home/akun/issue-tracker \
  -f prod_env_file=/home/akun/issue-tracker/prod.env \
  -f deploy_prod=false \
  -f expected_deploy_sha=<exact-current-sha>
```

STOP: Do not dispatch this workflow until the exact final ref/SHA is stated and the user explicitly approves deploying that exact ref/SHA to UAT with UAT data preserved.

## STOP

Continue local non-destructive recovery, preflight, tests, docs, commits, and pushes as needed for the 24-hour effort. Stop before any destructive data operation, before overwriting UAT, and before any UAT or production operation whose exact branch/SHA/data policy has not been stated.
