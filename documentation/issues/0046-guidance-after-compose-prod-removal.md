# Issue 0046: Update Guidance After The Compose Production Job Is Removed

Status: backlog
Recommended model: claude-opus-5-5 medium
Category gates: `IT-6`
Sprint: Sprint 0007

## Problem

Issue 0038 removed `deploy-prod`, `prod_host` and `promote_prod` from `.github/workflows/local-pipeline.yml`. Text outside that lane's write scope still describes the job as present, or as not yet built:

- `.claude/skills/deploy-safety/SKILL.md` Facts: "`local-pipeline.yml` still has its job (`deploy-prod`, inputs `prod_host`/`promote_prod` …) … removal is Issue 0038", and "`deployment/k8s/` and `k3s-pipeline.yml` are Issue 0020 and don't exist yet" (both merged in #13).
- `.claude/rules/deployment.md:14`: mentions the `.8` production path (`deploy-prod`).
- `documentation/guides/k3s.md` step 12: "After cutover, disable the Compose production job in `local-pipeline.yml` (tracked as issue 0038)".

Load `guidance-change` before editing `.claude/`.

## Files In Scope

`.claude/skills/deploy-safety/SKILL.md`, `.claude/rules/deployment.md`, `documentation/guides/k3s.md` (step 12 sentence only).

## Acceptance Criteria

- [ ] `deploy-safety` Facts say `local-pipeline.yml` has no production job (dev verify + legacy Compose UAT only) and that production deploys go through `k3s-pipeline.yml` / `deployment/k8s/`.
- [ ] `grep -rn "prod_host\|deploy-prod\|don't exist yet" .claude` matches only `k3s-pipeline.yml` facts, if any.
- [ ] `k3s.md` step 12 no longer asks the owner to disable a job that is gone.
- [ ] `guidance-change` checks pass; `python -m ruff check . && python -m pytest -q tests` green.

## Category Checklists

`IT-6` Deployment And Configuration Drift: Verify compose files, env vars, health checks, explicit migrations, and workflow behavior stay aligned.

## Verification Commands

```bash
grep -rn "prod_host\|promote_prod\|deploy-prod\|192.168.10.8" .claude documentation/guides
```

## STOP

Stop when guidance matches the workflows on `main`. Don't dispatch any pipeline or reach `192.168.10.x` or the cluster. Wait for Issue 0038's PR to merge first.
