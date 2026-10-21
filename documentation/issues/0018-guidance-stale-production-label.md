# Issue 0018: Remove Stale "Mislabels Production" Guidance

Status: done (this PR; guidance commit 7dc2867)
Recommended model: claude-opus-5-5 medium
Category gates: `IT-6`
Sprint: Sprint 0007

## Problem

Issue 0015 renamed the `local-pipeline.yml` production job (`prod_host`, `promote_prod`, `deploy-prod`, `environment: prod`). Claude guidance still says the pipeline mislabels `192.168.10.8` as `dev_host`, which is now false: `CLAUDE.md` (Tripwires, deploys), `.claude/skills/deploy-safety/SKILL.md` (Facts), `.claude/rules/deployment.md`. Found during 0015; outside that lane's write scope.

Since then the owner moved production to k3s (Issue 0020, 2026-10-20): production = namespace `issue-tracker`, UAT = `issue-tracker-uat`, and the `.8` Compose production path is retired. Guidance must say that, not just fix the label.

## Acceptance Criteria

- [x] No file under `CLAUDE.md` / `.claude/` says the pipeline mislabels `.8` or names `dev_host`/`promote_dev`. Evidence (7dc2867): `grep -rn -i "mislabel\|dev_host\|promote_dev" CLAUDE.md .claude` → no output, exit 1.
- [x] `deploy-safety` Facts name `prod_host`, `promote_prod`, `deploy-prod`, `environment: prod`, the same-SHA guard, and the `DEPLOY_ENV` backup refusal. Evidence (7dc2867): all six are in the Facts "Retired" and `remote-compose-deploy.sh` bullets. Each matches `local-pipeline.yml` (lines 14, 26, 83, 89, 92) and the script's `case "$deploy_env" in uat|prod` refusal (exit 2).
- [x] Production is k3s namespace `issue-tracker` and UAT `issue-tracker-uat` in `CLAUDE.md` (Tripwires), `.claude/skills/deploy-safety/SKILL.md` (description, Facts, Gates), `.claude/rules/deployment.md`, `.claude/README.md`; each says the `.8` Compose production path is retired. Evidence (7dc2867): `grep -rln "issue-tracker-uat" CLAUDE.md .claude` → all 4 files; `grep -rn "192.168.10.8" CLAUDE.md .claude` → only the "retired" lines in `CLAUDE.md`, `.claude/README.md`, `deploy-safety`.
- [x] Edit follows `guidance-change` (vibecoding mirror is updated by `mirror-rules.yml`, not by hand). Evidence: `CLAUDE.md` 93 lines (≤110), `deploy-safety` 48 (≤80), `rules/deployment.md` 18 (≤20); no skill added/renamed, so the index is unchanged; every cited path exists except `deployment/k8s/` and `k3s-pipeline.yml`, which are explicitly described as not built (Issue 0020); no vibecoding edits. Out-of-scope drift (pipeline + `documentation/guides/deployment.md` still offer the `.8` deploy) → [Issue 0035](0035-retire-compose-production-path.md).

## Category Checklists

`IT-6` Deployment And Configuration Drift: Verify compose files, env vars, health checks, explicit migrations, and workflow behavior stay aligned.

## Verification Commands

```bash
grep -rn -i "mislabel\|dev_host\|promote_dev" CLAUDE.md .claude
grep -rn "192.168.10.8\|issue-tracker-uat" CLAUDE.md .claude
```

## STOP

Stop when the grep returns nothing and the skill facts match the workflow.

Closed by claude-opus-5-5 (effort: medium).
