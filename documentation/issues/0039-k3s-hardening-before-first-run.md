# Issue 0039: Harden The k3s Deploy And Restore Path Before The First Real-Cluster Run

Status: in-progress (PR #22; second review round in progress)
Recommended model: claude-opus-5-5 high
Category gates: `IT-6`, `IT-3`
Sprint: Sprint 0007

## Context

An independent re-review of Issue 0020 (PR #13, merged as `5a7db65`) found these gaps in the k3s
pipeline, `deploy.sh`, `restore.sh` and `documentation/guides/k3s.md`. They must be fixed before the
owner's first real-cluster run.

## Files in scope

`deployment/k8s/` (scripts, manifests, tests), `.github/workflows/image.yml`,
`.github/workflows/k3s-pipeline.yml`, the `k8s` job in `.github/workflows/ci.yml`,
`documentation/guides/k3s.md`, this file.

## Acceptance Criteria

Evidence: CI run https://github.com/spacemanspiff99/issue-tracker/actions/runs/39545103929 (head `87b13ec`), job `k8s`. File:line refs are as of that commit.

- [x] **N1: `deploy-prod` fails unless the ref is `main`.**
  - `k3s-pipeline.yml:128` refuses any other ref, in addition to the `prod` environment branch rule.
  - `deployment/k8s/tests/pipeline-gates.py` case "prod: branch refused" passes in CI.
- [x] **NB1: timed-out restore.**
  - `restore.sh:105-111` deletes the Job (foreground, so an uncommitted transaction rolls back), leaves the app at 0 replicas, and says the database is either unchanged or fully restored. It never says "unchanged" on a timeout.
  - kind (`kind-smoke.sh:218`) printed "restore timed out after 60s; Job … deleted; app left at 0 replicas" and "ok: timed-out restore left the app at 0 and 20 projects in place".
- [x] **NB2: `--require-empty` handles an absent table.**
  - The guard uses `EXECUTE` (`restore-job.sh:24-40`), so a missing `projects` table is never planned.
  - Reproduced on local PG16: the old guard fails with `relation "public.projects" does not exist`; the new guard passes on an absent and an empty table and refuses on rows.
  - kind (`kind-smoke.sh:166,171,…`) printed "passed with an empty projects table", "passed with no projects table; schema restored at 0004…", and "ERROR: projects has 20 row(s); refusing to overwrite", with the 20 projects left in place.
- [x] **NB3: safety dump, and no deploy during a restore.**
  - `restore-job.sh:11-19` writes and verifies `/backups/pre-restore/<ts>-<pod>.dump` before anything is dropped, keeps the newest 5, and the CronJob prunes the same way.
  - `deploy.sh:108-112` refuses while a `component=restore` Job is active, and `restore.sh:36-37` refuses a second restore.
  - kind printed "pre-restore dumps: 2", "refusing: restore Job(s) still active … fake-restore" and "refusing: another restore Job is active".
- [x] **NB4: kubeconfigs kept for later steps.** `k3s.md:103-125` keeps them at `~/.kube/issue-tracker-{uat,prod}.yaml` (0600) on the admin machine. Steps 11 and 12, "Off-cluster copies" and "Restore" all use those paths, and the guide says how to revoke and rotate them.
- [x] **NB5: cutover runs the rehearsal's commit and digest.**
  - `image.yml:35-43` never rebuilds an already-pushed SHA, so one commit always has one digest.
  - The new `expected_image` input is checked in both deploy jobs (`k3s-pipeline.yml:70,134`).
  - Guide steps 12b and 12c record the rehearsal digest and pass it.
  - Gate cases "expected_image differs: refuse" (UAT and prod) pass in CI.
- [x] **NB6: write window closed.**
  - `deploy.sh:118-131` scales the app to 0 for backup + migrate and scales the old app back up if either fails. That is safe because Alembic runs all revisions in one transaction (`migrations/env.py:39`).
  - The reasoning is in `k3s.md` "Why the maintenance window".
  - kind printed "maintenance: app scaled to 0 for backup + migrate" and "ok: app was scaled to 0 for backup + migrate and came back".
- [x] **NB7: UAT deploys only from `main` by default.**
  - `k3s-pipeline.yml:66` refuses a non-main ref unless `allow_non_main_uat: true`. `promote_prod` from a branch is refused even with that override.
  - All 14 gate cases pass in CI (CI step "Pipeline ref and digest gates", `ci.yml:143`).
- [x] **NB8: Postgres pinned.** Every Postgres image in `deployment/k8s` is `postgres:16.15` (16.15 is what the kind run reported). The CI step "Postgres images pinned to a minor version" (`ci.yml:145`) fails on an unpinned one.
- [ ] **Review 2, B1:** a migrate or backup failure (timeout, cancel) deletes both Jobs (foreground, waits until their pods are gone) and brings the old app back only if `alembic_version` is provably unchanged. Otherwise the app stays at 0 with instructions. Proven in kind with a lock-blocked migration (stays at 0) and a failing backup (old app back).
- [ ] **Review 2, N1:** `restore.sh --keep-app-down`. The guide's rollback order is restore, then set image, then scale up, and it says UAT must be restored too before a revert passes the UAT stage.
- [ ] **Review 2, N2:** the image job fails on any `imagetools inspect` error other than "not found".
- [ ] **Review 2, N3:** `promote_prod` requires `expected_image` (gate cases in CI).
- [ ] **Review 2, N4:** a missing Deployment is detected with `--ignore-not-found`, so any other API error fails the deploy instead of skipping the maintenance window.
- [ ] **Review 2, N5:** an old pod that is still running at the timeout aborts the deploy before the backup, and the guide has a "Found the app at 0 replicas" section.
- [ ] **CI green on the final head.**

Review 2's N6 and N7 are tracked in Issue 0040.

## Category Checklists

`IT-6` Deployment And Configuration Drift: Verify compose files, env vars, health checks, explicit migrations, and workflow behavior stay aligned.
`IT-3` Schema And Migration Safety: Verify SQLAlchemy models, PostgreSQL constraints, and Alembic migrations agree; run migration checks on an empty database.

## Verification

```bash
python -m ruff check . && python -m pytest -q tests
python3 deployment/k8s/tests/pipeline-gates.py
# CI `k8s` job: render + kubeconform, digest renders, postgres pin guard, kind-smoke.sh
```

## STOP

Stop when every AC passes in CI on a disposable kind cluster. Do not reach 192.168.10.x or the real
cluster. Out of scope here: the `schema` CI job's `postgres:16` service, and
`docker-compose.local.yml`'s `postgres:16-alpine`. Both are other lanes' files.
