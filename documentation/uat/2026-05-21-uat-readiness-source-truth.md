# UAT Readiness Source-Of-Truth Check

Date: 2026-05-21

## Source State

- Branch: `deploy/app-host-targets`
- Local `HEAD`: `832b8ea4cbf8996ad0f6cd168a541e25664e4950`
- Upstream: `origin/deploy/app-host-targets`
- Upstream SHA: `6f0997054764aac938fe39965686e286208590fc`
- Status: local branch is behind upstream by 4 commits and has substantial uncommitted changes.

## Deployment Decision

UAT deployment was not dispatched.

Reason: GitHub Actions can deploy only committed code from the selected ref. The local dev checkout contains uncommitted product, schema, deployment, rule, and documentation changes, so deploying the current branch would not make UAT match dev. The operator must either commit and push the intended state, or explicitly choose a named older SHA to deploy.

## Safety Checks Added

- `.github/workflows/local-pipeline.yml` now requires `expected_deploy_sha`.
- `deployment/scripts/remote-compose-deploy.sh` refuses deployment when `GITHUB_SHA` does not match `EXPECTED_DEPLOY_SHA`.
- Deployment logs print source ref, source SHA, target environment, pre-migration backup path, and final deployed SHA.
- Local Docker preflight guidance now uses unique Compose project, PostgreSQL container, and app port values to avoid disrupting dev at `http://192.168.10.20:8000`.

## Verification Results

- `bash -n deployment/scripts/remote-compose-deploy.sh`: pass.
- `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/local-pipeline.yml')); print('workflow yaml ok')"`: pass.
- `COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml config`: pass; resolved project `issue_tracker_preflight`, PostgreSQL container `issue-tracker-preflight-postgres`, app port `18000`.
- `COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/`: pass; 47 passed, 1 skipped.
- `COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml run --rm app python -m ruff check --no-cache .`: pass.
- `curl -fsS http://192.168.10.20:8000/health` before and after preflight: pass, `{"ok":true,"database":"ok"}`.
- `curl -fsS http://192.168.10.26:8000/health`: pass, `{"ok":true,"database":"ok"}`.
- UAT workflow dispatch: not run because source-of-truth gate blocked deployment.

## Remaining Before UAT

1. Decide whether UAT should deploy the current dirty dev state or a named older SHA.
2. If deploying current dev, commit the intended product, schema, deployment, rule, and documentation changes.
3. Push the intended branch/ref.
4. Dispatch `.github/workflows/local-pipeline.yml` with `expected_deploy_sha` set to the exact pushed SHA and `deploy_prod=false`.
5. Record workflow run URL, pre-migration backup path, `/health`, MCP smoke, route/browser checks, and any blocked manual UAT items.

## 2026-05-22 Resume After Host Shutdown

The dev and preflight containers were stopped after a hard shutdown. The normal dev stack was restarted with:

```bash
docker compose -f deployment/docker-compose.local.yml up -d
```

This reused the existing local PostgreSQL volume. No reset, restore, or volume replacement was run.

Resume verification:

- `curl -fsS http://192.168.10.20:8000/health`: pass, `{"ok":true,"database":"ok"}` after restarting dev.
- `curl -fsS http://127.0.0.1:8000/health`: pass, `{"ok":true,"database":"ok"}`.
- `COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml config`: pass; resolved project `issue_tracker_preflight`, PostgreSQL container `issue-tracker-preflight-postgres`, app port `18000`.
- `COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/`: pass; 47 passed, 1 skipped. The skipped test is the opt-in browser UAT.
- `COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml run --rm app python -m ruff check --no-cache .`: pass.
- `curl -fsS http://192.168.10.20:8000/health` after isolated preflight: pass, `{"ok":true,"database":"ok"}`.
- `curl -fsS http://192.168.10.26:8000/health`: fail, connection refused.

UAT deployment remains blocked by the source-of-truth gate: local `deploy/app-host-targets` is still behind `origin/deploy/app-host-targets` and has substantial uncommitted product, schema, deployment, rule, and documentation changes. Do not dispatch UAT until the intended state is committed and pushed, or the user explicitly chooses a named older SHA.
