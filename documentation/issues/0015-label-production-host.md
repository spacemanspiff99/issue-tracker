# Issue 0015: Label 192.168.10.8 As Production In The Pipeline

Status: backlog
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

- [ ] No file labels `192.168.10.8` as dev.
- [ ] Production job depends on UAT, takes a backup before migrating, and checks `/health` database status.
- [ ] GitHub `prod` environment protection is configured (owner action; record when done).

## Category Checklists

`IT-6` Deployment And Configuration Drift: Verify compose files, env vars, health checks, explicit migrations, and workflow behavior stay aligned.

## Verification Commands

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/local-pipeline.yml'))"
grep -rn "192.168.10.8" .github documentation deployment
```

## STOP

Stop when the workflow and docs say production, or record the owner action still needed.
