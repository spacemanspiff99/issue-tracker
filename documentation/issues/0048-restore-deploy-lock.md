# Issue 0048: Restore/Deploy Concurrency Follow-Ups

Status: in-progress
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

- [ ] **1:** `restore.sh` refuses while a restore pod is live without an active Job, before the lock
  and again just before its Job. The Job then keeps only its own pin.
- [ ] **2:** `release_lock` deletes the lock only when `data.job` names this run (restore and deploy).
- [ ] **3:** `deploy.sh` takes `issue-tracker-restore-lock`, refuses if it is held, and releases it on
  exit with the same `job_may_run` rule (kept while the backup/migrate Jobs may still run).
- [ ] **4:** `fail-closed.sh` exits 2 with "needs kubectl" when kubectl is missing.
- [ ] **5:** the N-3 messages say "revision unchanged".
- [ ] Each item has a case that fails on `b35e8fb` (where applicable) and a mutation that it catches.
- [ ] CI 5/5, including the kind smoke.

## Category Checklists

`IT-6` Deployment And Configuration Drift: Verify compose files, env vars, health checks, explicit migrations, and workflow behavior stay aligned.

## Verification

```bash
bash deployment/k8s/tests/fail-closed.sh && bash deployment/k8s/tests/fail-closed-mutations.sh
# CI `k8s` job: deployment/k8s/tests/kind-smoke.sh
```

## STOP

Stop when every AC passes in CI. Do not reach 192.168.10.x or the real cluster.
