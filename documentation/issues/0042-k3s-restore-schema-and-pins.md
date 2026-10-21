# Issue 0042: k3s Restore: Schema-Matched Scale-Up, Leaked Pins, Concurrent Restores

Status: in-progress (PR #27, green on bc112f2; awaiting review)
Recommended model: claude-opus-5-5 high
Category gates: `IT-6`
Sprint: Sprint 0007

## Context

Non-blocking items from the round-4 review of Issue 0041 (PR #25, merged as `12b5ef3`). Each one
could bite on the first real run, so they are fixed before the release candidate.

## Files in scope

`deployment/k8s/restore.sh`, `deployment/k8s/restore-job.sh`, `deployment/k8s/tests/`
(`fail-closed.sh`, `fail-closed-mutations.sh`, `kind-smoke.sh`), `documentation/guides/k3s.md`,
this file (and the Status line of Issue 0041).

## Acceptance Criteria

Evidence: CI run https://github.com/spacemanspiff99/issue-tracker/actions/runs/39584140073 (head `bc112f2`, 5/5 green), job `k8s`.

- [x] **N1:** `restore-job.sh` logs `alembic_version before restore:` / `after restore:` (`(none)` when the table is absent; any other read error fails the Job before the transaction). After a successful restore without `--keep-app-down`, `restore.sh` returns the app to its previous count only when both match; otherwise the app stays at 0, the script exits 1 and names both versions and the Rollback steps. The generic pre-migration example in `k3s.md` Restore uses `--keep-app-down`, and the Outcomes list covers the case.
  - kind: "restored /backups/pre-migration/553b087…dump into issue-tracker-uat, and alembic_version went from '0003_fake_other' to '0004_reconcile_schema_drift'", with the app left at 0.
  - kind: the same-revision restore printed "ok: same-revision restore brought the app back to 1 replica".
- [x] **N2:** `restore-job.sh` runs `rm -fv /backups/restoring/*.dump` before pinning its dump.
  - Local PG16 with a planted leaked hard link: on `12b5ef3` it survives the restore (dump at 2 links); after the fix it is removed (1 link).
  - kind: a planted pin printed "removed '/backups/restoring/killed-pod.dump'", and `/backups/restoring` was empty afterwards. The timed-out restore case also leaked a real pin (its SIGKILLed pod), and the next restore printed "removed '/backups/restoring/issue-tracker-restore-20261021103553-nsbnp.dump'".
  - The optional SIGTERM trap is not added: bash runs it only after the `psql` pipeline returns, so it could exit between COMMIT and the "restore committed" line, which `restore.sh` would read as "not committed".
- [x] **N3:** `fail-closed.sh` cases: success at 1 → 1, success at 2 → 2, success at 0 stays 0, and a failure before COMMIT at 2 → 2. `EXPECT_REPLICAS` requires the last scale to equal that count, with no scale above it.
- [x] **N4:** `restore.sh` re-checks for an active restore Job right before `kubectl create` (not `apply`) of its own. Case "another restore started meanwhile (N4)": another restore becomes active on the second read, and no Job is created.
- [x] **Before/after:** on `12b5ef3` the 4 new regression cases FAIL (N1 ×3: schema changed, versions not in the logs, logs unreadable; N4); after the fix all 42 cases pass. Mutations: 10/10 caught, 2 new (N1 forced `schema_same=1`; N4 re-check skipped). The "Job status unreadable" case now has same-revision logs, so its mutation still bites now that N1 holds the app down.
- [x] **CI 5/5** on `bc112f2`: "fail-closed checks passed", "all mutations caught", "kind smoke passed".

## Category Checklists

`IT-6` Deployment And Configuration Drift: Verify compose files, env vars, health checks, explicit migrations, and workflow behavior stay aligned.

## Verification

```bash
bash deployment/k8s/tests/fail-closed.sh && bash deployment/k8s/tests/fail-closed-mutations.sh
# CI `k8s` job: deployment/k8s/tests/kind-smoke.sh
```

## STOP

Stop when every AC passes in CI. Do not reach 192.168.10.x or the real cluster.
