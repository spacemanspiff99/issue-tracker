# Issue 0017: Remove Stale "Mislabels Production" Guidance

Status: backlog
Recommended model: claude-opus-5-5 medium
Category gates: `IT-6`
Sprint: Sprint 0007

## Problem

Issue 0015 renamed the `local-pipeline.yml` production job (`prod_host`, `promote_prod`, `deploy-prod`, `environment: prod`). Claude guidance still says the pipeline mislabels `192.168.10.8` as `dev_host`, which is now false: `CLAUDE.md` (Tripwires, deploys), `.claude/skills/deploy-safety/SKILL.md` (Facts), `.claude/rules/deployment.md`. Found during 0015; outside that lane's write scope.

## Acceptance Criteria

- [ ] No file under `CLAUDE.md` / `.claude/` says the pipeline mislabels `.8` or names `dev_host`/`promote_dev`.
- [ ] `deploy-safety` Facts name `prod_host`, `promote_prod`, `deploy-prod`, `environment: prod`, the same-SHA guard, and the `DEPLOY_ENV` backup refusal.
- [ ] Edit follows `guidance-change` (vibecoding mirror is updated by `mirror-rules.yml`, not by hand).

## Category Checklists

`IT-6` Deployment And Configuration Drift: Verify compose files, env vars, health checks, explicit migrations, and workflow behavior stay aligned.

## Verification Commands

```bash
grep -rn -i "mislabel\|dev_host\|promote_dev" CLAUDE.md .claude
```

## STOP

Stop when the grep returns nothing and the skill facts match the workflow.
