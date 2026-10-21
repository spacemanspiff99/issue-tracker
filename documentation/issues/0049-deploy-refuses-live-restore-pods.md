# Issue 0049: deploy.sh Refuses While A Restore Pod Is Live

Status: in-progress (PR #31, green on 8c9db81; awaiting review)
Recommended model: claude-opus-5-5 high
Category gates: `IT-6`
Sprint: Sprint 0007

## Context

`restore.sh` refuses while a restore pod is live without an active Job (Issue 0048). `deploy.sh`
only checked restore Jobs, so a restore pod that outlived its Job (or was made by hand) could still
be writing while a deploy backed up and migrated.

## Files in scope

`deployment/k8s/deploy.sh`, `deployment/k8s/restore.sh`, `deployment/k8s/lib.sh` (new, shared
`live_restore_pods`), `deployment/k8s/tests/` (`fail-closed.sh`, `fail-closed-mutations.sh`,
`kind-smoke.sh`), `documentation/guides/k3s.md`, this file.

## Acceptance Criteria

Evidence: CI run https://github.com/spacemanspiff99/issue-tracker/actions/runs/39651046019 (head `8c9db81`, 5/5 green), job `k8s`.

- [x] `deploy.sh` refuses while a restore pod is live (not Succeeded/Failed) without an active Job,
  before it takes the lock and again just before the backup Job, using the same
  `live_restore_pods` as `restore.sh` (`lib.sh`).
- [x] A refusal before the lock leaves the app and the lock untouched; a refusal before the backup
  brings the old app back and releases the lock.
- [x] Cases fail on `016bae6` and pass after; a mutation of each check is caught. On `016bae6` 4 cases FAIL: live pod and pod started meanwhile ("exited 0"), and the pod list unreadable before the lock and before the backup. Control: finished pods don't block. Mutations: each check skipped ("true", "if false"), and the shared awk filter emptied in `lib.sh`.
- [x] CI 5/5 on `8c9db81`, including the kind smoke: "ok: refused: deploy while a restore pod is live" and "ok: restore and deploy refused while a restore pod was live; app and lock untouched".

## Category Checklists

`IT-6` Deployment And Configuration Drift: Verify compose files, env vars, health checks, explicit migrations, and workflow behavior stay aligned.

## Verification

```bash
bash deployment/k8s/tests/fail-closed.sh && bash deployment/k8s/tests/fail-closed-mutations.sh
# CI `k8s` job: deployment/k8s/tests/kind-smoke.sh
```

## STOP

Stop when every AC passes in CI. Do not reach 192.168.10.x or the real cluster.
