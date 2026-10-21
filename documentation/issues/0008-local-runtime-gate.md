# Issue 0008: Local Runtime Gate For Manual UAT

Status: in-progress — dev-path (Compose) AC pass at `cac4a09`; k3s UAT AC marked OWNER are open.
Recommended model: GPT-5.5 high
Category gates: `IT-3`, `IT-6`
Sprint: Sprint 0007

## Problem

Manual UAT cannot start until the local Docker runtime proves it can build the app, start PostgreSQL, run explicit migrations, run tests, and serve `/health` with database connectivity.

## Scope

- Verify Docker daemon access and record the owner action if unavailable.
- Build the local app image from `deployment/docker-compose.local.yml`.
- Run `alembic upgrade head` explicitly against local PostgreSQL.
- Run the full pytest suite through the app service.
- Start the local stack and verify `/health`.
- Record exact commands and pass/fail evidence in the sprint closeout.

## Acceptance Criteria

UAT runs on k3s `issue-tracker-uat` ([`k3s.md`](../guides/k3s.md)); Docker Compose is the dev path.
Dev-path evidence: cloud container, Docker 29.9.1, fresh volume (`down -v`), app code at `cac4a09`
(merge of `main` @ `5a7db65` + seed-demo guard). Full table: [UAT notes](../uat/2026-10-20-cloud-container-uat-readiness.md).

Dev path (local Docker Compose):

- [x] `docker compose -f deployment/docker-compose.local.yml build` completes without host Python setup. CI `e2e` builds and starts the compose stack on a clean runner with no host Python (`$COMPOSE up -d --build postgres app`; [run 39545418717, job `e2e`](https://github.com/spacemanspiff99/issue-tracker/actions/runs/39545418717/job/119042384075) on `cac4a09`). In the cloud container `build` as written is blocked by environment only (pip/apt TLS through the session proxy); the image was built from the same context minus the `playwright install --with-deps` line, see notes.
- [x] `... run --rm app alembic upgrade head` succeeds against local PostgreSQL → `0001_initial → 0002_guidance_sync → 0003_guidance_audit_events → 0004_reconcile_schema_drift` on a fresh volume (`cac4a09`).
- [x] `... run --rm app python -m pytest tests/` passes → `70 passed, 22 skipped` (`cac4a09`; e2e skipped without `RUN_BROWSER_UAT`). `... run --rm app python -m ruff check --no-cache .` → `All checks passed!` (plain `ruff check .` in the container → [0045](0045-ruff-in-app-container-cache-permission.md)).
- [x] `... up -d` starts app and PostgreSQL (`cac4a09`).
- [x] `GET /health` returns app readiness and database connectivity → `curl -fsS http://localhost:8000/health` = `{"ok":true,"database":"ok"}` (`cac4a09`).
- [x] No `.env`, logs, database dumps, backups, generated exports, or local credentials are committed → `git status --short` after the run shows only intended source/doc files; `artifacts/`, `exports/` gitignored.

UAT (k3s `issue-tracker-uat`) — needs the real cluster:

- [ ] **OWNER** — Actions → **k3s UAT Production Pipeline** → Run workflow on `main` (after this PR merges) with `promote_prod: false`. Expected in the log: pushed digest `ghcr.io/spacemanspiff99/issue-tracker@sha256:…`; backup Job writes `/backups/pre-migration/<sha>-<ts>.dump`; migrate Job runs `alembic upgrade head` (`… -> 0004_reconcile_schema_drift` on an empty DB); rollout complete; `health: {"ok": true, "database": "ok"}` in the pod and through the ingress; browser suite `22 passed`, artifact `uat-e2e-screenshots-<sha>`. Record the run URL + SHA here.
- [ ] **OWNER** — `K="kubectl -n issue-tracker-uat"; $K get deploy issue-tracker -o jsonpath='{.spec.template.spec.containers[0].image}'` → the same `@sha256:` digest as that run; `curl -fsS http://issue-tracker-uat.home.arpa/health` → `{"ok":true,"database":"ok"}`.

Originating model: claude-opus-5-5 (effort: medium).

## Category Checklists

`IT-3` Schema And Migration Safety: Verify SQLAlchemy models, PostgreSQL constraints, and Alembic migrations agree; run migration checks on an empty database.

`IT-6` Deployment And Configuration Drift: Verify compose files, env vars, health checks, explicit migrations, and workflow behavior stay aligned.

## Verification Commands

Dev path:

```bash
docker compose -f deployment/docker-compose.local.yml config -q
docker compose -f deployment/docker-compose.local.yml build
docker compose -f deployment/docker-compose.local.yml run --rm app alembic upgrade head
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/
docker compose -f deployment/docker-compose.local.yml up -d && curl -fsS http://localhost:8000/health
```

UAT (owner, cluster access): the pipeline run above, then

```bash
K="kubectl -n issue-tracker-uat"
$K get deploy issue-tracker -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
curl -fsS http://issue-tracker-uat.home.arpa/health
```

## STOP

Stop when the local runtime is proven ready for browser UAT, or record the exact blocker, command output summary, owner action, and next retry step in Sprint 0007.
