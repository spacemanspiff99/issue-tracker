# Issue 0042: k3s Restore: Schema-Matched Scale-Up, Leaked Pins, Concurrent Restores

Status: in-progress
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

- [ ] **N1:** after a successful restore without `--keep-app-down`, the app comes back only if the
  Job logs show the same `alembic_version` before and after. A different revision, or logs that
  can't be read, leaves the app at 0 with a message naming both versions and the Rollback steps.
  The generic Restore example in `k3s.md` uses `--keep-app-down`.
- [ ] **N2:** `restore-job.sh` clears pins leaked in `/backups/restoring/` by a killed restore Job
  before pinning its own dump. Checked locally on PG16 and in kind.
- [ ] **N3:** `fail-closed.sh` covers the success path (back to the previous count; 0 stays 0) and a
  starting count of 2 (never above it), for success and for a failure before COMMIT.
- [ ] **N4:** `restore.sh` re-checks for an active restore Job right before it creates its own, and
  uses `kubectl create`, so a same-name Job is never silently reused.
- [ ] New regression cases fail on `12b5ef3` and pass after the fix; the new mutations are caught.
- [ ] CI 5/5.

## Category Checklists

`IT-6` Deployment And Configuration Drift: Verify compose files, env vars, health checks, explicit migrations, and workflow behavior stay aligned.

## Verification

```bash
bash deployment/k8s/tests/fail-closed.sh && bash deployment/k8s/tests/fail-closed-mutations.sh
# CI `k8s` job: deployment/k8s/tests/kind-smoke.sh
```

## STOP

Stop when every AC passes in CI. Do not reach 192.168.10.x or the real cluster.
