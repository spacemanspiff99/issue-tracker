# Issue 0015: Label 192.168.10.8 As Production In The Pipeline

Status: in-progress
Recommended model: claude-opus-5-5 high
Category gates: `IT-6`
Sprint: Sprint 0007

## Problem

`192.168.10.8` is home-lab production, but `.github/workflows/local-pipeline.yml` calls it `dev_host` / "Promote To Dev" with `promote_dev` and `environment: dev`. An operator or agent reading the workflow would treat a production deploy as disposable dev.

## Scope

- Rename inputs/job/environment to production (`prod_host`, `promote_prod`, "Deploy Production", `environment: prod` with a required-reviewer protection rule set by the owner in GitHub).
- Production job requires the UAT job green on the same SHA and never sets `SKIP_DB_BACKUP=1`.
- Update `documentation/guides/deployment.md`.

## Acceptance Criteria

- [x] No file labels `192.168.10.8` as dev. Evidence: `grep -rn -i "dev_host\|promote_dev\|downstream\|environment: dev\|promote to dev" .github documentation deployment` matches only `current_dev_host` (`192.168.10.20`, the real dev host) and this issue's Problem text; `grep -rn "192.168.10.8"` shows only production labels; YAML loads. Guidance outside this lane (`CLAUDE.md`, `.claude/`) still says "mislabels" → [Issue 0018](0018-guidance-stale-production-label.md).
- [x] Production job depends on UAT, takes a backup before migrating, and checks `/health` database status. Evidence: `deploy-prod` has `needs: deploy-uat`, `if: inputs.promote_prod && needs.deploy-uat.result == 'success'`, and a step refusing a SHA different from UAT's recorded SHA; `remote-compose-deploy.sh` refuses `SKIP_DB_BACKUP=1` for `DEPLOY_ENV=uat|prod` (stub run: exit 2) and the health loop requires `"database": "ok"` (stub run: `{"database":"error"}` → exit 1 after 10 attempts; healthy → exit 0 with `pg_dump` + `cp` logged before `alembic upgrade head`).
- [ ] GitHub `prod` environment protection is configured (owner action; record when done). Pending: owner creates `prod` under Settings -> Environments with a required reviewer.

## Category Checklists

`IT-6` Deployment And Configuration Drift: Verify compose files, env vars, health checks, explicit migrations, and workflow behavior stay aligned.

## Verification Commands

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/local-pipeline.yml'))"
grep -rn "192.168.10.8" .github documentation deployment
```

## STOP

Stop when the workflow and docs say production, or record the owner action still needed.

Blocked on owner: configure the GitHub `prod` environment with a required reviewer, then tick the last AC and set `Status: done`. Until then `deploy-prod` runs ungated by a reviewer if dispatched with `promote_prod: true` (an environment that does not exist is auto-created without protection).
