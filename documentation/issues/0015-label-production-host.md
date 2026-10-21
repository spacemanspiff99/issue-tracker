# Issue 0015: Label 192.168.10.8 As Production In The Pipeline

Status: done
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
- [x] GitHub `prod` environment protection is configured (owner action; record when done). Closed as moot by [Issue 0038](0038-retire-compose-production-path.md) (`claude/0038-retire-compose-production-path`, 8a2404a): `local-pipeline.yml` no longer has `deploy-prod`, `prod_host`, `promote_prod` or `environment: prod`, so no `.8` deploy exists to gate. The `prod` environment reviewer is still required for `k3s-pipeline.yml`; that owner action is `documentation/guides/k3s.md` step 8, tracked by Issue 0020.

## Category Checklists

`IT-6` Deployment And Configuration Drift: Verify compose files, env vars, health checks, explicit migrations, and workflow behavior stay aligned.

## Verification Commands

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/local-pipeline.yml'))"
grep -rn "192.168.10.8" .github documentation deployment
```

## STOP

Stop when the workflow and docs say production, or record the owner action still needed.

Blocked on owner: configure the GitHub `prod` environment with a required reviewer, then tick the last AC and set `Status: done`. Re-checked 2026-10-21: the renames are on `main` (`855ca7f`, #7), but the environment can't be read from a cloud session (`gh api .../environments` → HTTP 403 from the proxy), so the AC stays open. Production has since moved to k3s (Issue 0020), so the `.8` `deploy-prod` job is retired. [Issue 0038](0038-retire-compose-production-path.md) removes it, and that closes this AC as moot. Until then `deploy-prod` runs ungated by a reviewer if dispatched with `promote_prod: true` (an environment that does not exist is auto-created without protection).

Closed 2026-10-21 via Issue 0038: the last AC is moot because the job it gated is removed. Originating model: claude-opus-5-5 (effort: medium).
