# Issue 0038: Retire The 192.168.10.8 Compose Production Path In Pipeline And Docs

Status: backlog
Recommended model: claude-opus-5-5 high
Category gates: `IT-6`
Sprint: Sprint 0007

## Problem

Production is now k3s namespace `issue-tracker` (UAT `issue-tracker-uat`, Issue 0020), and the Compose production path on `192.168.10.8` is retired. Claude guidance says so (Issue 0018), but `.github/workflows/local-pipeline.yml` still has `deploy-prod` (`prod_host: 192.168.10.8`, `promote_prod`), and `documentation/guides/deployment.md` still documents `.8` as production. The GitHub `prod` environment reviewer (Issue 0015, owner action) is also unconfirmed, so a `promote_prod: true` dispatch could deploy to `.8` without a reviewer gate. Found during 0018; outside that lane's write scope (`documentation/issues/`, `CLAUDE.md`, `.claude/`).

## Files in scope

`.github/workflows/local-pipeline.yml`, `documentation/guides/deployment.md`, `deployment/scripts/remote-compose-deploy.sh` (only if `DEPLOY_ENV=prod` handling changes), `documentation/issues/0015-label-production-host.md`.

## Acceptance Criteria

- [ ] `local-pipeline.yml` has no production job and no `prod_host`/`promote_prod` inputs (or the job fails closed with a message pointing to the k3s pipeline). Evidence: YAML loads; `grep -n "prod_host\|promote_prod\|deploy-prod" .github/workflows/local-pipeline.yml` → none (or only the fail-closed step).
- [ ] `documentation/guides/deployment.md` names k3s `issue-tracker` as production and `issue-tracker-uat` as UAT, says the `.8` Compose path is retired, and keeps Compose for dev/local only.
- [ ] `grep -rn "192.168.10.8" .github documentation/guides deployment` shows no live production deploy instruction.
- [ ] Issue 0015's open AC (GitHub `prod` environment reviewer) is either closed as moot because the job is gone, or ticked with the owner's confirmation; 0015 set to `done`.
- [ ] Any data still on `.8` has an owner-approved move to k3s production recorded (backup first; this issue never touches `.8`).

## Category Checklists

`IT-6` Deployment And Configuration Drift: Verify compose files, env vars, health checks, explicit migrations, and workflow behavior stay aligned.

## Verification Commands

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/local-pipeline.yml'))"
grep -rn "192.168.10.8\|prod_host\|promote_prod" .github documentation/guides deployment
```

## STOP

Stop when the pipeline and guide no longer offer a `.8` production deploy. Do not dispatch any pipeline or reach `192.168.10.x` or the cluster; moving data off `.8` is an owner step.
