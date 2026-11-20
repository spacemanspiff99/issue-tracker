---
name: uat-deploy
description: Deploy an exact pushed commit to UAT on the dev host with deployment/scripts/local-uat-deploy.sh (local, no runners, isolated issue_tracker_uat stack). Use when the user asks to deploy, ship, or push to UAT. Production is not supported until issue 0178 (k3s). Not for data refresh; use data-refresh for that.
disable-model-invocation: true
---

# UAT Code Deploy (local, dev host)

Source of truth: `documentation/guides/deployment.md` ("Local UAT Deploy (No Runners)" and "UAT co-hosted on the dev host") and the Verification rules in `AGENTS.md`. If they disagree with this skill, the docs win; report the drift.

A deploy moves **code only**. It never copies, resets, or restores target data. UAT runs on the dev host `192.168.10.20` (`cursor-issue-tracker`) next to the live dev app. It must never touch the dev stack (project `deployment`, container `issue-tracker-postgres`, volume `deployment_issue_tracker_pgdata`, port `8000`).

Production: there is no supported deploy path. Production moves to k3s with a shared Postgres and vault (issue `0178`, `documentation/issues/0178-prod-k3s-shared-postgres.md`). The `.github/workflows/local-pipeline.yml` runner workflow is **superseded**. Do not dispatch it.

## 1. Source-of-truth gate (STOP on any mismatch)

```bash
git fetch origin
git status --short --branch
git rev-parse origin/dev
```

- The deploy source is `git archive <sha>`, so uncommitted local changes never deploy. If the user expects them to, STOP: they must be committed, merged to `dev` by PR, and pushed first.
- Default ref is `origin/dev`. Any other ref needs the user to name it explicitly.
- Record the **full 40-char SHA**.

## 2. Dry run (no changes)

```bash
DEPLOY_DRY_RUN=1 deployment/scripts/local-uat-deploy.sh <full-sha>
```

Pass only if it prints `DRY RUN: all guards passed`. Also check disk first: `df -h / /tmp` and `docker system df`.

## 3. State the operation, then wait for explicit confirmation

Report exactly:

- Operation: local code deploy via `deployment/scripts/local-uat-deploy.sh`
- SHA (full) and ref
- Target: `issue_tracker_uat` stack, `/home/akun/issue-tracker-uat`, port `8100`, container `issue-tracker-uat-postgres`
- Data: UAT volume `issue_tracker_uat_issue_tracker_pgdata` preserved, with a pre-migration backup under `/home/akun/issue-tracker-uat/backups/<sha>-<timestamp>/`. The dev volume is untouched.
- Migrations: forward-only `alembic upgrade head`
- Rollback outline: repoint `/home/akun/issue-tracker-uat/current` to the previous release and `up -d` with the UAT env. A data restore needs a separate, explicit request naming the backup.

Wait for the user to approve that exact SHA. Approval of an earlier SHA does not carry over.

## 4. Deploy and verify

```bash
deployment/scripts/local-uat-deploy.sh <full-sha>
curl -fsS http://192.168.10.20:8100/health
curl -fsS http://192.168.10.20:8000/health   # live dev must still be healthy, if it was running
```

The guard hook blocks the script without a full 40-char SHA. Pass only if: backup, Alembic, tests, ruff, `/health` (DB connected), MCP smoke, and browser UAT all pass, and the dev stack is unchanged.

Any manual compose command against UAT must carry `COMPOSE_PROJECT_NAME=issue_tracker_uat POSTGRES_CONTAINER_NAME=issue-tracker-uat-postgres APP_HTTP_PORT=8100`, run from `/home/akun/issue-tracker-uat/current`. Without these, compose targets the dev stack.

On failure: debug from the script output and `docker compose logs` (with the UAT env) before changing code. Do not re-run with different settings without telling the user.

## 5. Closeout

Report the deployed SHA, the release path, data **preserved** (with the backup path), check results, and anything blocked. Update the tracker issue or sprint evidence, plus a UAT note under `documentation/uat/` if this is a release gate.
