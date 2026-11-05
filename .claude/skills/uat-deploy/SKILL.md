---
name: uat-deploy
description: Deploy committed code to UAT (and optionally production) through the SHA-pinned local-pipeline GitHub Actions workflow. Use when the user asks to deploy, ship, or push to UAT or production. Not for data refresh; use data-refresh for that.
disable-model-invocation: true
---

# UAT / Production Code Deploy

Source of truth: `documentation/guides/deployment.md` and the Verification rules in `AGENTS.md`. If they disagree with this skill, the docs win; report the drift.

A deploy moves **code only**. It never copies, resets, or restores target data.

## 1. Source-of-truth gate (STOP on any mismatch)

```bash
git status --short --branch
git rev-parse HEAD
git rev-parse @{u}
git fetch origin && git rev-parse origin/$(git branch --show-current)
```

- Uncommitted product, UI, schema, deployment, or doc changes: STOP. Offer to commit and push them, or ask the user to name an older SHA explicitly.
- Local `HEAD` differs from the remote ref: STOP and resolve it (push, or pick the remote SHA explicitly).
- Record the branch and the **full 40-char SHA** that will deploy.

## 2. State the operation, then wait for explicit confirmation

Report exactly:

- Operation: code deploy via `.github/workflows/local-pipeline.yml`
- Target: UAT `192.168.10.26` (hostname `app-uat`), plus production `192.168.10.27` only if `deploy_prod=true`
- Ref and SHA
- Data: preserved; the workflow takes a pre-migration backup under `/home/akun/issue-tracker/backups/<sha>-<timestamp>/`
- Migrations: forward-only `alembic upgrade head`
- Rollback outline: redeploy the previous SHA; a data restore needs a separate, explicit request naming the backup

Production (`deploy_prod=true`) needs its own explicit "deploy to production" from the user. UAT approval does not carry over.

## 3. Dispatch

```bash
gh workflow run local-pipeline.yml --ref <branch> \
  -f expected_deploy_sha=<full-sha> \
  -f uat_host=192.168.10.26 \
  -f prod_host=192.168.10.27 \
  -f deploy_user=akun \
  -f deploy_path=/home/akun/issue-tracker \
  -f prod_env_file=/home/akun/issue-tracker/prod.env \
  -f deploy_prod=false
```

The project guard hook blocks dispatch without a full `expected_deploy_sha`.

## 4. Watch and verify

```bash
gh run list --workflow local-pipeline.yml --limit 3
gh run watch <run-id> --exit-status
```

Pass only if: the "Verify deploy source" step shows `GITHUB_SHA == expected_deploy_sha`; backup, Alembic, tests, ruff, `/health` (DB connected), MCP smoke, and browser UAT all pass.

On failure: debug from the run logs (`gh run view <id> --log-failed`) before changing code. Do not re-dispatch with different inputs without telling the user.

## 5. Closeout

Report: deployed SHA, run URL, target(s), data **preserved** (backup path if shown), check results, and anything blocked. Update the tracker issue or sprint evidence, plus a UAT note under `documentation/uat/` if this is a release gate.
