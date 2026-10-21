# Issue 0041: k3s Cutover Polish Before The First Real Run

Status: in-progress (PR #25; review-1 fixes pushed)
Recommended model: claude-opus-5-5 high
Category gates: `IT-6`
Sprint: Sprint 0007

## Context

The round-2 review of Issue 0039 (PR #22, merged as `4e1eb61`) said MERGE and recommended these
cheap items before the owner's first real cutover.

## Files in scope

`deployment/k8s/restore.sh`, `deployment/k8s/tests/kind-smoke.sh`, `.github/workflows/image.yml`,
`documentation/guides/k3s.md`, this file.

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

Review 1 of PR #25:
- [ ] **B1: `wait_app_gone` fails closed.** It captures `kubectl get pods --request-timeout=10s` and returns 1 if kubectl fails, so a failed list never counts as "gone". `deployment/k8s/tests/fail-closed.sh` (no cluster; stub kubectl whose `get pods` fails) runs the real scripts:
  - `deploy.sh` must abort in the maintenance window, never apply the backup or migrate Job, and scale the old app back to 1.
  - `restore.sh` must abort before creating any ConfigMap or Job.
  - The same test fails against the `3fe776e` scripts: the old `deploy.sh` went on to the backup after "connection refused".
- [ ] **N1:** when `restore.sh` aborts because the app won't stop, it prints the next steps. The "Found the app at 0 replicas" intro now lists that case.
- [ ] **N3:** `k3s.md` now says a third run for the same SHA can cancel the waiting image job; that run ends cancelled before any deploy.
- [ ] **N4:** the kind PV-release wait fails after 120s instead of carrying on.
- [ ] CI 5/5 on the new head.

## Category Checklists

`IT-6` Deployment And Configuration Drift: Verify compose files, env vars, health checks, explicit migrations, and workflow behavior stay aligned.

## Verification

CI `k8s` job (`deployment/k8s/tests/kind-smoke.sh`); `python -m ruff check . && python -m pytest -q tests`.

## STOP

Stop when every AC passes in CI. Do not reach 192.168.10.x or the real cluster.
