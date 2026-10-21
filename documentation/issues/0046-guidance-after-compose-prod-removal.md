# Issue 0046: Update Guidance After The Compose Production Job Is Removed

Status: in-progress (PR open; close on merge)
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

`.claude/skills/deploy-safety/SKILL.md`, `.claude/rules/deployment.md`, `documentation/guides/k3s.md` (step 12 sentence only). Added by the PR #21 review (finding 1): `README.md:49`, `documentation/sprints/0007-local-manual-uat-readiness.md:71`, `documentation/prompts/0016-production-readiness-orchestrator.md` (superseded banner only).

## Acceptance Criteria

- [x] `deploy-safety` Facts say `local-pipeline.yml` has no production job (dev verify + legacy Compose UAT only) and that production deploys go through `k3s-pipeline.yml` / `deployment/k8s/`.
- [x] `grep -rn "prod_host\|deploy-prod\|don't exist yet" .claude` matches only `k3s-pipeline.yml` facts, if any.
- [x] `k3s.md` step 12 no longer asks the owner to disable a job that is gone.
- [x] `guidance-change` checks pass; `python -m ruff check . && python -m pytest -q tests` green.

## Category Checklists

`IT-6` Deployment And Configuration Drift: Verify compose files, env vars, health checks, explicit migrations, and workflow behavior stay aligned.

## Verification Commands

```bash
grep -rn "prod_host\|promote_prod\|deploy-prod\|192.168.10.8" .claude documentation/guides
```

## STOP

Stop when guidance matches the workflows on `main`. Don't dispatch any pipeline or reach `192.168.10.x` or the cluster. Wait for Issue 0038's PR to merge first.


## Evidence

- Facts now describe `k3s-pipeline.yml`, `image.yml` digests, `deploy.sh`, `restore.sh` (`CONFIRM`, `--require-empty`) and `local-pipeline.yml` as dev + legacy UAT only; pointer to `k3s.md`.
- `grep -rn "prod_host\|deploy-prod\|don't exist yet" .claude` → only the `k3s-pipeline.yml` `deploy-prod` fact.
- `k3s.md` step 12 no longer asks to disable the removed job.
- Budgets: deploy-safety 52 lines (≤80), rules/deployment.md 18 (≤20); no skill renamed.
- The scale-to-0 maintenance-window fact is deferred until PR #22 (0039) merges.
