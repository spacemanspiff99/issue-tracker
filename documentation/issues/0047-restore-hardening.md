# Issue 0047: restore.sh Hardening From The #27 Review

Status: in-progress (PR #28, green on 1af5b52; awaiting review)
Recommended model: claude-opus-5-5 high
Category gates: `IT-6`
Sprint: Sprint 0007

## Context

Follow-ups from the review of Issue 0042 (PR #27, merged as `b0490e3`): make concurrent restores
impossible rather than unlikely, never touch another restore's pin, and bring the app back after a
failed restore only when the schema revision is proven unchanged.

## Files in scope

`deployment/k8s/restore.sh`, `deployment/k8s/restore-job.sh`, `deployment/k8s/tests/`
(`fail-closed.sh`, `fail-closed-mutations.sh`, `kind-smoke.sh`), `documentation/guides/k3s.md`,
this file.

## Acceptance Criteria

Evidence: CI run https://github.com/spacemanspiff99/issue-tracker/actions/runs/39592605128 (head `1af5b52`, 5/5 green), job `k8s`.

- [x] **N-1: restore lock.** `restore.sh` takes the lock with `kubectl create configmap issue-tracker-restore-lock` before it changes anything. The create is atomic: if the ConfigMap exists, the restore is refused with the steps to clear a stale lock. `release_lock` runs on exit, and also on INT/TERM. While `job_may_run=1` (from just before the Job is created until its outcome is known, or until it is confirmed deleted) the lock is kept and the script says so. The comment above the Job re-check now says it catches restore Jobs made another way, and that `create` refuses an existing name.
  - Cases: lock held → refuses, lock left; lock create fails → refuses, lock left; released after success; released when the app can't be stopped; kept when the timed-out Job can't be deleted.
  - kind: "refusing: could not take the restore lock …", with the lock and the app (1 replica) untouched. The lock is gone after the N1/N-2 restore and after the timed-out restore.
- [x] **N-2: own pins only.** `restore.sh` passes `KEEP_PINS`, the restore pods not yet Succeeded or Failed. `restore-job.sh` removes leaked pins, never one in `KEEP_PINS`, and leaves its own pin to its EXIT trap.
  - Case `[job] leaked pin removed, running pod's pin kept`: runs `restore-job.sh` against stub psql, pg_dump and pg_restore with `BACKUPS_ROOT` set to a scratch dir. Against `b0490e3`'s script (with only the path made configurable) it fails with "removed the pin of a running restore pod".
  - Case: restore pods unreadable → aborts before the Job, lock released.
  - kind: "keeping pin of running restore pod fake-running-restore" and "removed '/backups/restoring/killed-pod.dump'". The timed-out case's real leaked pin was also removed: "removed '/backups/restoring/issue-tracker-restore-20261021114446-6sw22.dump'".
- [x] **N-3: version re-read on failure.** The Job reads `alembic_version` first. Its EXIT trap re-reads it on any failure ("alembic_version after failed restore: …"). After a failure, `restore.sh` scales the app back only if the logs show no COMMIT and the version is unchanged. Otherwise the app stays at 0 and the message gives both versions.
  - Cases: failed with the version changed → app at 0; failed with no after-failed line (killed between COMMIT and its log line) → app at 0. On `b0490e3` that second case scaled the app up.
  - Job-side case: a failed transaction logs the after-failed version.
  - Local PG16: a `--require-empty` refusal logged "before restore: 0004_head" and "after failed restore: 0004_head"; a success logged 0004_head → 0003_old.
- [x] **N-4: exactly one line per version.** `log_value` returns a value only when there is exactly one matching line. Cases: duplicate lines on success and on failure → app at 0.
- [x] **Before/after:** against `b0490e3`, all 13 new cases FAIL; after the fix, 55/55 pass. Mutations: 17/17 caught, including 7 new ones (N-1 ×3, N-2, N-3 ×2, N-4). Two existing cases changed so their mutations still bite: N1 targets `schema_same=…`, and "Job failed, logs unreadable" now models a cut-off log stream.
- [x] **CI 5/5** on `1af5b52`: "fail-closed checks passed", "all mutations caught", "kind smoke passed".

Not changed: `deploy.sh` doesn't take the restore lock. It still refuses only while a restore Job is active, and the guide says not to restore during a deploy.

## Category Checklists

`IT-6` Deployment And Configuration Drift: Verify compose files, env vars, health checks, explicit migrations, and workflow behavior stay aligned.

## Verification

```bash
bash deployment/k8s/tests/fail-closed.sh && bash deployment/k8s/tests/fail-closed-mutations.sh
# CI `k8s` job: deployment/k8s/tests/kind-smoke.sh
```

## STOP

Stop when every AC passes in CI. Do not reach 192.168.10.x or the real cluster.
