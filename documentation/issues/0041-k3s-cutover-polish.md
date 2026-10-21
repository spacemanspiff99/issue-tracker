# Issue 0041: k3s Cutover Polish Before The First Real Run

Status: in-progress (PR #25, review-3 fixes green on c9fb9c6; awaiting re-review)
Recommended model: claude-opus-5-5 high
Category gates: `IT-6`
Sprint: Sprint 0007

## Context

The round-2 review of Issue 0039 (PR #22, merged as `4e1eb61`) said MERGE and recommended these
cheap items before the owner's first real cutover.

## Files in scope

`deployment/k8s/deploy.sh`, `deployment/k8s/restore.sh`, `deployment/k8s/restore-job.sh`,
`deployment/k8s/base/postgres.yaml`, `deployment/k8s/tests/` (`kind-smoke.sh`, `fail-closed.sh`,
`fail-closed-mutations.sh`), `.github/workflows/image.yml`, the `k8s` job in
`.github/workflows/ci.yml`, `documentation/guides/k3s.md`, this file.

## Acceptance Criteria

Evidence: CI run https://github.com/spacemanspiff99/issue-tracker/actions/runs/39554798198 (head `2578a4a`, 5/5 green), job `k8s`. Line refs are as of `2578a4a`.

- [x] **BLOCKER (from #22, seen in PR #14's k8s job, run 39554288587): first deploy into a fresh namespace raced Postgres's init.**
  - Cause: on a fresh volume the entrypoint first runs a temporary socket-only server before `CREATE DATABASE`. The socket `pg_isready` passed, and `db_version` hit `FATAL: database "issue_tracker" does not exist`.
  - Fix: the probes use TCP (`postgres.yaml:68,72`, `pg_isready -h 127.0.0.1`). `deploy.sh:143-153` waits in a bounded loop for a TCP `select 1` before reading the version, and on timeout fails with a clear message plus the Postgres log.
  - kind (`kind-smoke.sh:360`): 3 extra first deploys, each into a deleted and recreated namespace and volume. Each printed "postgres: accepting connections", "alembic_version before deploy: (none)" and a healthy `/health`, then "ok: fresh deploy 1/2/3". The main first deploy passed too.
- [x] **NB1: `restore.sh` aborts before the dump if the app can't be stopped.**
  - The scale-to-0 and the pod wait no longer have `|| true` (`restore.sh:50-70`); only a missing Deployment is tolerated.
  - kind (`kind-smoke.sh:264`), app pod held by a finalizer: printed "app pod still present after 120s" and "ok: restore aborted before any restore Job when the app pod would not stop".
- [x] **NB2:** `k3s.md:317` ("A cancelled run is different") says a GitHub cancel force-kills the step about 10s after the signal, so the cleanup usually doesn't finish; expect the app at 0 with the migrate Job maybe still running, and see "Found the app at 0 replicas".
- [x] **NB3:** both cutover restores in `k3s.md` use `--keep-app-down` (`k3s.md:267`, `k3s.md:286`), and the text says the next deploy migrates the data and brings the app up.
- [x] **NB4:** `image.yml:28` adds the concurrency group `image-${{ github.sha }}`. `k3s.md:216-221` and step 12c now give both causes of a digest mismatch (`main` moved, or the GHCR tag was deleted or overwritten) and explain the concurrency group.
- [x] **NB5: migrate timeout with the version unchanged brings the old app back.** kind (`kind-smoke.sh:233`): a quota blocked the migrate pod, and the log showed "deploy failed during: migrate", then "Jobs deleted and alembic_version unchanged (0004_reconcile_schema_drift); restoring the previous app (replicas=1)", then "ok: migrate timed out -> … old app scaled back up".
- [x] **Also found and fixed:** `kubectl wait --for=delete pod -l …` errors ("no matching resources") when the selector is already empty. Both scripts now poll with `wait_app_gone` (`deploy.sh:120`, `restore.sh:50`).
- [x] **CI green on the PR:** 5/5 on `2578a4a`.

Review 1 of PR #25 (evidence: CI run https://github.com/spacemanspiff99/issue-tracker/actions/runs/39560958862, head `b6ea2d4`, 5/5 green):
- [x] **B1: `wait_app_gone` fails closed.** It captures `kubectl get pods --request-timeout=10s` and returns 1 if kubectl fails, so a failed list never counts as "gone". `deployment/k8s/tests/fail-closed.sh` (no cluster; stub kubectl whose `get pods` fails) runs the real scripts:
  - `deploy.sh` must abort in the maintenance window, never apply the backup or migrate Job, and scale the old app back to 1.
  - `restore.sh` must abort before creating any ConfigMap or Job.
  - The same test fails against the `3fe776e` scripts: the old `deploy.sh` went on to the backup after "connection refused".
  - CI step "deploy.sh and restore.sh fail closed when pods can't be listed" printed "ok: deploy.sh aborted before the backup and restored the previous app", "ok: restore.sh aborted before any ConfigMap or Job" and "fail-closed checks passed".
- [x] **N1:** when `restore.sh` aborts because the app won't stop, it prints the next steps. The "Found the app at 0 replicas" intro now lists that case.
- [x] **N3:** `k3s.md` now says a third run for the same SHA can cancel the waiting image job; that run ends cancelled before any deploy.
- [x] **N4:** the kind PV-release wait fails after 120s instead of carrying on.
- [x] CI 5/5 on the new head (`b6ea2d4`); the kind smoke passed in full, including the NB1/NB5 cases and 3 fresh deploys.

Review 2 of PR #25, the fail-open pattern fixed as a class (evidence: CI run https://github.com/spacemanspiff99/issue-tracker/actions/runs/39568621931, head `7d81ad9`, 5/5 green; audit comment https://github.com/spacemanspiff99/issue-tracker/pull/25#issuecomment-6311460380):
- [x] **B2:** `restore.sh` decided "is there an app?" with `kubectl … -o name | grep -q .`. A kubectl error took the else branch ("nothing to stop") and went on to the restore. It now decides on the `.spec.replicas` read alone (`--ignore-not-found`, fails under `set -e`).
- [x] **Audit:** every kubectl and psql call whose result decides whether to proceed, in `deploy.sh`, `restore.sh`, `backup-files.sh`, `e2e.sh`, `restore-job.sh` and the Job/CronJob scripts. Each one now fails closed on error, and "not found" is only ever read via `--ignore-not-found` with a successful exit. The list of decision points, with file:line and how each fails closed, is in a comment on PR #25.
  - NB-a: the "Job active?" checks no longer use `2>/dev/null || true`.
  - `restore.sh`'s post-Job handling: status reads, logs and delete each fail closed.
  - `deploy.sh`'s `on_failure` checks exit codes explicitly.
- [x] **NB-b:** `deploy.sh` waits for app pods whenever the Deployment exists, even at 0 replicas.
- [x] **Test:** `tests/fail-closed.sh` failed one chosen kubectl call per case at that point (14 `deploy.sh` and 8 `restore.sh` decision points, plus the NB-b state case; the 9th `restore.sh` "case" was the B2 placeholder that only read "n/a" and is removed in review 3) and asserts that nothing irreversible is applied. Against `d249aa3` it fails 6 cases (NB-a ×4, NB-b, B2); against this branch it passes them all.
- [x] **NB-c:** the guide notes the one-time Postgres restart on the first deploy after the probe change.
- [x] **NB-d:** the `--keep-app-down` next-step text covers the no-Deployment case.
- [x] CI 5/5 on `7d81ad9`. The CI fail-closed step passed all cases, and the kind smoke passed in full: blocked migration, failing backup, migrate timeout and 3 fresh deploys.

Review 3 of PR #25 (evidence: CI run https://github.com/spacemanspiff99/issue-tracker/actions/runs/39575931159, head `c9fb9c6`, 5/5 green):
- [x] **B1:** `restore.sh` remembers the app's previous replica count. After a pre-COMMIT failure (and after success) the app goes back to that count, never above it, and stays at 0 if it was at 0 or `--keep-app-down` was given. Before, an app at 0 came back at 1 even with `--keep-app-down`.
- [x] **Tests after the Jobs are applied:** `fail-closed.sh` has 34 cases. New ones:
  - deploy: the `wait_job` read fails, alone and together with each `on_failure` check
  - restore: the status poll, the logs and the timeout delete each fail
  - B1: 3 cases, app at 0 with and without `--keep-app-down`, and `--keep-app-down` at 1
  - a positive control
  - The 3 B1 cases fail on `2d22fc0` and pass now.
- [x] **Mutation check:** `tests/fail-closed-mutations.sh` (new, CI) re-introduces 8 fail-open patterns into a copy of the scripts and requires the matching case to FAIL. Among them is `|| true` on the restore logs read (the regression the reviewer found the suite missed). All 8 are caught.
- [x] **NB2 placeholder:** removed (the B2 "n/a" case); case counts above corrected.
- [x] **NB3:** `restore-job.sh` pins the dump with a hard link in `/backups/restoring/` (outside every pruned folder) and restores from the pin. It prunes `pre-restore` only after COMMIT, never counting or deleting the restored dump. Checked locally on PG16 by restoring the oldest of 7 pre-restore dumps: it survived, the newest 5 others were kept, and the pin was removed.
- [x] **NB4:** `k3s.md` Restore: don't run a restore while a pipeline deploy is running.
- [x] **NB5:** "Files in scope" above now lists every file this issue changed.
- [x] CI 5/5 on `c9fb9c6`: 34 fail-closed cases ok, "all mutations caught" (8/8), and the kind smoke passed (the absent-table restore left the app at 0, then 3 fresh deploys).

## Category Checklists

`IT-6` Deployment And Configuration Drift: Verify compose files, env vars, health checks, explicit migrations, and workflow behavior stay aligned.

## Verification

CI `k8s` job (`deployment/k8s/tests/kind-smoke.sh`); `python -m ruff check . && python -m pytest -q tests`.

## STOP

Stop when every AC passes in CI. Do not reach 192.168.10.x or the real cluster.
