# Issue 0047: restore.sh Hardening From The #27 Review

Status: in-progress
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

- [ ] **N-1:** `restore.sh` takes an atomic lock (`kubectl create configmap issue-tracker-restore-lock`)
  before it changes anything, refuses if it exists, and releases it on exit, except while its Job may
  still be running. The comment above the Job re-check says what the re-check is for now.
- [ ] **N-2:** the Job removes only its own pin and pins leaked by killed restore Jobs, never the pin of
  a restore pod that `restore.sh` saw still running (`KEEP_PINS`).
- [ ] **N-3:** on any failure the Job re-reads `alembic_version` and logs it; `restore.sh` scales the app
  back only if it equals the version from before the restore, otherwise leaves it at 0 with both
  versions in the message.
- [ ] **N-4:** `restore.sh` reads each version only from exactly one log line; a missing or repeated
  line counts as unknown (app stays at 0).
- [ ] Each item has a `fail-closed.sh` case that fails on `b0490e3` and passes after the fix, and a
  mutation in `fail-closed-mutations.sh` that the case catches.
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
