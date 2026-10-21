# Issue 0048: Restore/Deploy Concurrency Follow-Ups

Status: done (PR #30; follow-ups in Issues 0049, 0050)
Recommended model: claude-opus-5-5 high
Category gates: `IT-6`
Sprint: Sprint 0007

## Context

Non-blocking notes from the review of Issue 0047 (PR #28, merged as `b35e8fb`): close the remaining
restore/deploy overlaps, and make the lock and test harness stricter.

## Files in scope

`deployment/k8s/restore.sh`, `deployment/k8s/restore-job.sh`, `deployment/k8s/deploy.sh`,
`deployment/k8s/tests/` (`fail-closed.sh`, `fail-closed-mutations.sh`, `kind-smoke.sh`),
`documentation/guides/k3s.md`, this file (and the Status line of Issue 0047).

## Acceptance Criteria

Evidence: CI run https://github.com/spacemanspiff99/issue-tracker/actions/runs/39599719190 (head `c7f24f1`, 5/5 green), job `k8s`.

- [x] **1: live restore pods refused.** `restore.sh` refuses while a restore pod is live (not Succeeded or Failed) without an active Job. `live_restore_pods` runs before the lock and again just before the Job. The Job then removes every pin but its own, and `KEEP_PINS` is gone.
  - Cases: a live pod refuses before anything; a pod that starts meanwhile is refused before the Job; the pod list unreadable before and after the lock. Control: finished pods don't block. `[job] every pin but its own removed`.
  - kind: "refusing: restore pod(s) still running in issue-tracker-uat without an active Job: fake-running-restore", with the app (1) and the lock untouched. The next restore removed `killed-pod.dump` and `killed-pod-2.dump`, and `/backups/restoring` was empty afterwards.
- [x] **2: holder-only release.** `release_lock` deletes the lock only when `data.job` names this run, in both `restore.sh` and `deploy.sh`. An unreadable holder means the lock is not released. Cases: holder changed (restore and deploy); holder unreadable.
- [x] **3: deploy takes the lock.** `deploy.sh` takes `issue-tracker-restore-lock` after its active-Job checks, and refuses if it is held. It releases the lock on every exit (`on_failure`, the rollout-phase trap, INT/TERM), but keeps it while `job_may_run=1`. That flag is set just before the backup Job, and cleared after the migrate Job completes or `on_failure` confirms both Jobs gone.
  - Cases: lock held: refuses; create fails; released after success; released after a failure before the Jobs; released when the Jobs are confirmed gone; kept when they may still run.
  - kind: the main deploy left no lock; "ok: deploy refused while the restore lock was held; lock left to its holder".
- [x] **4:** `fail-closed.sh` checks for kubectl first and exits 2 with "needs kubectl". CI: "ok   fail-closed.sh without kubectl: exit 2, \"needs kubectl\"". The same check run against a copy with the check deleted reports it missing.
- [x] **5:** the messages now say "revision unchanged (<rev>)" and "not proven that the revision is unchanged". The control case expects "revision unchanged (0004_x)".
- [x] **Before/after:** against `b35e8fb`, 14 new or changed cases FAIL; the finished-pods control and the Job-side pin case pass there, as expected. After the fix, 67/67 pass. Mutations: 23 caught, 7 of them new (#1, #2 ×2, #3 ×3, #5), plus the missing-kubectl check and its mutant (#4).
- [x] **CI 5/5** on `c7f24f1`: "fail-closed checks passed", "all mutations caught", "kind smoke passed".

Residual: the holder check before the delete isn't atomic, since kubectl can't delete with a precondition. A lock removed by hand and re-taken in that window could still be deleted.

## Category Checklists

`IT-6` Deployment And Configuration Drift: Verify compose files, env vars, health checks, explicit migrations, and workflow behavior stay aligned.

## Verification

```bash
bash deployment/k8s/tests/fail-closed.sh && bash deployment/k8s/tests/fail-closed-mutations.sh
# CI `k8s` job: deployment/k8s/tests/kind-smoke.sh
```

## STOP

Stop when every AC passes in CI. Do not reach 192.168.10.x or the real cluster.
