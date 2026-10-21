# Issue 0050: deploy.sh Cleanup Survives A Second INT/TERM

Status: in-progress
Recommended model: claude-opus-5-5 high
Category gates: `IT-6`
Sprint: Sprint 0007

## Context

`on_failure` reset INT and TERM to their defaults before deleting the backup/migrate Jobs, so a
second Ctrl-C (or a runner's TERM after its INT) killed the script mid-cleanup: no summary, the
old app not brought back, and the lock not released.

## Files in scope

`deployment/k8s/deploy.sh`, `deployment/k8s/tests/` (`fail-closed.sh`, `fail-closed-mutations.sh`),
`documentation/guides/k3s.md`, this file.

## Acceptance Criteria

- [ ] `on_failure` ignores further INT/TERM while it runs, and still prints its summary, restores
  the old app when safe, and releases the lock.
- [ ] Every cleanup step stays bounded: the Job deletion keeps `--timeout=180s`; the Job read, the
  scale-back and the lock calls use `--request-timeout=30s`; the version read uses
  `--request-timeout=60s` on top of its `lock_timeout`/`statement_timeout`.
- [ ] Cases (TERM+INT during the Job deletion and during the Job check) fail on `016bae6` and pass
  after; reverting to `trap - INT TERM` is caught.
- [ ] CI 5/5.

## Category Checklists

`IT-6` Deployment And Configuration Drift: Verify compose files, env vars, health checks, explicit migrations, and workflow behavior stay aligned.

## Verification

```bash
bash deployment/k8s/tests/fail-closed.sh && bash deployment/k8s/tests/fail-closed-mutations.sh
```

## STOP

Stop when every AC passes in CI. Do not reach 192.168.10.x or the real cluster.
