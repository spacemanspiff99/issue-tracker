# Sprint 0112: UAT Deploy And Comprehensive Test Suite

Status: active in the local tracker

Tracker sprint: `0112` Deploy committed dev state to UAT and run comprehensive UAT suite

Created: 2026-05-22

Source context:

- UAT readiness evidence: `documentation/uat/2026-05-21-uat-readiness-source-truth.md`
- Deployment guide: `documentation/guides/deployment.md`
- Comprehensive test plan: `documentation/guides/comprehensive-test-plan.md`
- Fresh-session source-of-truth prompt: `documentation/prompts/0111-deployment-source-truth-and-uat-readiness.md`

## Recommendation

Do not deploy UAT from the older pushed branch tip if the goal is for UAT to match dev.

The current checkout contains substantial uncommitted product, schema, deployment, rule, and documentation changes, while branch `deploy/app-host-targets` is behind `origin/deploy/app-host-targets` by four commits. GitHub Actions can deploy only committed pushed code, so deploying the older SHA would verify the pipeline but would not verify the application state now visible in dev.

Recommended path:

1. Preserve and commit the intended dev state before branch integration.
2. Reconcile with the upstream branch without losing local work.
3. Run isolated local preflight on the final candidate SHA.
4. Push that exact SHA.
5. Dispatch UAT with `expected_deploy_sha` equal to the pushed SHA and `deploy_prod=false`.
6. Run the comprehensive UAT suite against `app-uat` / `192.168.10.26`.

## Intake And Backlog Review

Tracker review on 2026-05-22:

- Active project: `issue-tracker`.
- Open active-project backlog before this sprint: none.
- Existing active-project sprints: `0043`, `0050`, `0073`, `0078`, `0084`, `0109`, and `0110` are closed.
- Voice/audio/intake matches in the active project: `0048`, `0071`, `0074`, `0079`, `0080`, `0081`, `0082`, and `0083`; all are `DONE`.
- Inactive browser/manual UAT projects contain duplicate old test issues and are intentionally ignored for this release sprint.

This sprint adds the next active backlog: `0113` through `0118`.

## Model And Reasoning

Recommended model/reasoning: GPT-5.5 `high`.

Use high reasoning because this sprint touches deployment source-of-truth, UAT data preservation, schema/migration verification, GitHub Actions dispatch, browser UAT, and release evidence.

## Scope

| Order | Tracker ID | Phase | Priority | Issue |
|---:|---|---|---|---|
| 1 | `0113` | Source of truth | high | Freeze and commit intended dev state for UAT |
| 2 | `0114` | Local verification | high | Run isolated local preflight on the UAT candidate SHA |
| 3 | `0115` | Guarded deploy | high | Push exact UAT candidate SHA and dispatch guarded workflow |
| 4 | `0116` | UAT deploy verification | high | Verify UAT deployment preserves target data and passes health gates |
| 5 | `0117` | UAT test suite | high | Run comprehensive UAT suite against the UAT host |
| 6 | `0118` | Closeout | high | Record UAT evidence and release decision handoff |

## Dependency-Aware Plan

### Phase A: Source-Of-Truth Candidate

Issue: `0113`

Deliver:

- Review `git status --short --branch` and exclude secrets, generated exports, backups, raw audio, screenshots, local certs, and `.env` files.
- Commit the intended dev state locally before integrating upstream.
- Reconcile with `origin/deploy/app-host-targets`, or choose a new explicit branch if that is cleaner.
- Record the final candidate SHA.

STOP if merge/rebase conflicts require product decisions, or if the candidate contains artifacts that must not be committed.

### Phase B: Local Candidate Preflight

Issue: `0114`

Deliver:

- Confirm dev health before preflight: `curl -fsS http://192.168.10.20:8000/health`.
- Run isolated Compose checks with:

```bash
COMPOSE_PROJECT_NAME=issue_tracker_preflight \
POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres \
APP_HTTP_PORT=18000 \
docker compose -f deployment/docker-compose.local.yml config
```

- Run migration, full tests, ruff, MCP smoke, and explicit browser UAT where available against the candidate.
- Confirm dev health after preflight.

STOP if any local gate fails.

### Phase C: Guarded UAT Deploy

Issue: `0115`

Deliver:

- Push the candidate branch/ref.
- Confirm local `HEAD` and remote SHA match.
- Dispatch `.github/workflows/local-pipeline.yml` with `expected_deploy_sha=<candidate-sha>` and `deploy_prod=false`.
- Record workflow run ID and URL.

STOP if intended UAT changes remain uncommitted or unpushed.

### Phase D: UAT Deployment Safety

Issue: `0116`

Deliver:

- Verify the workflow deploys to `app-uat` / `192.168.10.26`.
- Verify workflow source SHA equals `expected_deploy_sha`.
- Verify pre-migration backup path exists and is non-empty.
- Verify Alembic runs only forward with `upgrade head`.
- Verify no UAT data reset, volume replacement, restore, or dev-data copy occurred.
- Verify `http://192.168.10.26:8000/health`.
- Verify MCP smoke.

STOP if backup, migration, source SHA, or health verification fails.

### Phase E: Comprehensive UAT Suite

Issue: `0117`

Deliver:

- Run browser UAT against `UAT_BASE_URL=http://192.168.10.26:8000`, not local dev.
- Cover desktop and mobile viewports.
- Cover setup/login, project, issue, dependency, sprint, closeout, backlog, board, releases, intake, guidance sync, backup, planning, and categories surfaces.
- Record any manual-only or credential-gated checks with owner action.

STOP if UAT has a user-visible regression that prevents a release decision.

### Phase F: Evidence And Release Decision

Issue: `0118`

Deliver:

- Add a dated UAT-host evidence note under `documentation/uat/`.
- Update this sprint doc with deployed SHA, workflow run ID, target URL, backup path, verification commands, pass/fail results, and blockers.
- Close tracker issues only after their acceptance criteria pass.
- State one release decision: ready for further manual exploratory UAT, blocked by named owner action, or not ready with specific regressions.

STOP if evidence is incomplete.

## Local Preflight Evidence

Local preflight evidence is recorded in `documentation/uat/2026-05-22-sprint-0112-local-preflight.md`.

Current completed gates:

- Local source-of-truth freeze committed and rebased onto `origin/deploy/app-host-targets`.
- Container test suite passed.
- Ruff passed.
- MCP smoke passed.
- Empty-database Alembic upgrade reached head.
- Isolated browser UAT passed against a containerized app.

## Verification Commands

Source-of-truth:

```bash
git status --short --branch
git rev-parse HEAD
git rev-parse --abbrev-ref --symbolic-full-name @{u}
git rev-parse @{u}
```

Local isolated preflight:

```bash
curl -fsS http://192.168.10.20:8000/health
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml config
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml run --rm app alembic upgrade head
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml run --rm app python -m issue_tracker.mcp.server --smoke
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml run --rm app python -m ruff check --no-cache .
curl -fsS http://192.168.10.20:8000/health
```

Browser UAT:

```bash
docker compose -f deployment/docker-compose.local.yml exec -e RUN_BROWSER_UAT=1 app python -m pytest tests/e2e/
```

UAT deployment:

```bash
gh workflow run local-pipeline.yml --ref <branch-or-sha> \
  -f expected_deploy_sha=<exact-candidate-sha> \
  -f uat_host=192.168.10.26 \
  -f prod_host=192.168.10.27 \
  -f deploy_user=akun \
  -f deploy_path=/home/akun/issue-tracker \
  -f prod_env_file=/home/akun/issue-tracker/prod.env \
  -f deploy_prod=false
gh run list --workflow local-pipeline.yml --limit 5
gh run watch <run-id> --exit-status
curl -fsS http://192.168.10.26:8000/health
```

UAT-host comprehensive checks:

```bash
UAT_BASE_URL=http://192.168.10.26:8000 RUN_BROWSER_UAT=1 python -m pytest tests/e2e/
```

If the host Python/Playwright environment is not available, run the equivalent containerized/browser-capable command and record the exact environment used.

## STOP

Sprint `0112` is not complete until UAT is deployed from the exact pushed candidate SHA, UAT data preservation is evidenced, the comprehensive UAT suite has been run against the UAT host, and tracker plus markdown closeout evidence is complete.

If blocked, the STOP handoff must name the specific blocker owner action: source-control conflict, uncommitted intended code, failed local gate, failed workflow, failed backup, failed migration, UAT health failure, UAT browser regression, missing credentials, or missing browser-capable test environment.
