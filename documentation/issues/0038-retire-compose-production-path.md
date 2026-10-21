# Issue 0038: Retire The 192.168.10.8 Compose Production Path In Pipeline And Docs

Status: in-progress
Recommended model: claude-opus-5-5 high
Category gates: `IT-6`
Sprint: Sprint 0007

## Problem

Production is now k3s namespace `issue-tracker` (UAT `issue-tracker-uat`, Issue 0020), and the Compose production path on `192.168.10.8` is retired. Claude guidance says so (Issue 0018), but `.github/workflows/local-pipeline.yml` still has `deploy-prod` (`prod_host: 192.168.10.8`, `promote_prod`), and `documentation/guides/deployment.md` still documents `.8` as production. The GitHub `prod` environment reviewer (Issue 0015, owner action) is also unconfirmed, so a `promote_prod: true` dispatch could deploy to `.8` without a reviewer gate. Found during 0018; outside that lane's write scope (`documentation/issues/`, `CLAUDE.md`, `.claude/`).

## Files in scope

`.github/workflows/local-pipeline.yml`, `documentation/guides/deployment.md`, `deployment/scripts/remote-compose-deploy.sh` (only if `DEPLOY_ENV=prod` handling changes), `documentation/issues/0015-label-production-host.md`.

## Acceptance Criteria

- [x] `local-pipeline.yml` has no production job and no `prod_host`/`promote_prod` inputs (or the job fails closed with a message pointing to the k3s pipeline). Evidence: YAML loads; `grep -n "prod_host\|promote_prod\|deploy-prod" .github/workflows/local-pipeline.yml` → none (or only the fail-closed step). Result (8a2404a): `yaml.safe_load` OK, jobs `['verify-current-dev', 'deploy-uat']`, inputs `['current_dev_host', 'uat_host', 'deploy_user', 'deploy_path']`; the grep prints nothing (exit 1). Header comment points to `k3s-pipeline.yml`.
- [x] `documentation/guides/deployment.md` names k3s `issue-tracker` as production and `issue-tracker-uat` as UAT, says the `.8` Compose path is retired, and keeps Compose for dev/local only. Evidence (8a2404a): environment table at the top (Production = k3s `issue-tracker`, UAT = k3s `issue-tracker-uat`, Dev = Compose); "The Compose production path on `192.168.10.8` is retired"; the pipeline section is now "Local Runner Compose Pipeline (dev + legacy UAT)" with no production step, input, host, SSH target or URL. The `.18` legacy Compose UAT host stays until the owner's k3s cutover (`k3s.md` step 12), as `deploy-safety` already records.
- [x] `grep -rn "192.168.10.8" .github documentation/guides deployment` shows no live production deploy instruction. Result (8a2404a): `.github/workflows/local-pipeline.yml:5` (retired comment), `documentation/guides/deployment.md:9` (retired notice), and `documentation/guides/k3s.md:216,223` (step 12: dump data off `.8` for the k3s restore — an export, not a deploy). `deployment/` has none. `remote-compose-deploy.sh` unchanged: with no `prod` caller its `uat|prod` backup refusal still fails safe.
- [x] Issue 0015's open AC (GitHub `prod` environment reviewer) is either closed as moot because the job is gone, or ticked with the owner's confirmation; 0015 set to `done`. Closed as moot in this PR: the `.8` job and its `environment: prod` use are gone. The `prod` reviewer still gates `k3s-pipeline.yml`; that owner action is `k3s.md` step 8, tracked by Issue 0020.
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

Status: AC 1–4 met on branch `claude/0038-retire-compose-production-path` (8a2404a); `python -m ruff check . && python -m pytest -q tests` → `All checks passed!`, `54 passed, 22 skipped`. AC 5 is open and blocked on the owner: run `k3s.md` step 12 (stop writers on `.8`, `pg_dump`, `restore.sh --require-empty` into k3s production) and record the approval and result here. This issue never touches `.8`. Close (`Status: done`) once the PR merges with CI green and AC 5 is recorded. Stale guidance this change leaves (`deploy-safety`, `.claude/rules/deployment.md`, `k3s.md` step 12 note) → [Issue 0046](0046-guidance-after-compose-prod-removal.md). Originating model: claude-opus-5-5 (effort: medium).
