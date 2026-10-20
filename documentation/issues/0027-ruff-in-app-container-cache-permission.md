# Issue 0027: `ruff check` Fails Inside The App Container

Status: backlog
Recommended model: claude-opus-5-5 low
Category gates: `IT-6`
Sprint: Sprint 0007

## Context

Found by issue 0008 runtime gate on 2026-10-20 (commit `a98b164`). The `uat-gate` step
`docker compose -f deployment/docker-compose.local.yml run --rm app python -m ruff check .` fails:
the image runs as `appuser`, `/app` is root-owned, so ruff cannot create `/app/.ruff_cache`
(`Cause: No such file or directory (os error 2) at path "/app/.ruff_cache/0.17.1/..."`).
`ruff check --no-cache .` passes (`All checks passed!`). CI runs ruff on the host, so it does not see this.

## Files in scope

`deployment/Dockerfile` (writable cache dir or `RUFF_CACHE_DIR`), or `pyproject.toml` `[tool.ruff] cache-dir`,
and the `uat-gate` command if it changes.

## Acceptance Criteria

- [ ] `docker compose -f deployment/docker-compose.local.yml run --rm app python -m ruff check .` passes on a fresh build.
- [ ] No cache files land in the bind-mounted source tree or in git.

## Category Checklists

`IT-6` Deployment And Configuration Drift: Verify compose files, env vars, health checks, explicit migrations, and workflow behavior stay aligned.

## Verification Commands

```bash
docker compose -f deployment/docker-compose.local.yml build
docker compose -f deployment/docker-compose.local.yml run --rm app python -m ruff check .
```

## STOP

Stop when the in-container ruff command passes.
