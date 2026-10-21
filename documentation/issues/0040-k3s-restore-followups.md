# Issue 0040: k3s Restore Follow-Ups (Silent Scale-Up, Safety-Dump Retention)

Status: backlog
Recommended model: claude-opus-5-5 high
Category gates: `IT-6`
Sprint: Sprint 0007

## Context

These are leftovers from the independent review of Issue 0039 (PR #22). They are not blocking for
the first real-cluster run, so they are tracked here instead of being widened into #22.

## Files in scope

`deployment/k8s/deploy.sh`, `deployment/k8s/restore-job.sh`, `deployment/k8s/base/backup-cronjob.yaml`,
`deployment/k8s/tests/kind-smoke.sh`, `documentation/guides/k3s.md`, this file.

## Acceptance Criteria

- [ ] N6: `deploy.sh` no longer silently scales an app that a timed-out restore (or `--keep-app-down`) left at 0. When the Deployment exists at 0 replicas, it refuses unless an explicit input or environment variable acknowledges the state. The pipeline exposes that input, and the guide's "Found the app at 0 replicas" section names it. A kind test covers both the refusal and the override.
- [ ] N7: pruning never rotates out the only safety dump taken before an incident. `pre-restore` (and `pre-migration`) retention keeps the oldest dump of the last N days as well as the newest 5, or keeps by age. The CronJob and `restore-job.sh` agree, and a kind test seeds dumps and checks what survives.
- [ ] The CI `k8s` job is green.

## Category Checklists

`IT-6` Deployment And Configuration Drift: Verify compose files, env vars, health checks, explicit migrations, and workflow behavior stay aligned.

## Verification

CI `k8s` job (`deployment/k8s/tests/kind-smoke.sh`).

## STOP

Stop when both items pass in kind. Do not reach 192.168.10.x or the real cluster.
