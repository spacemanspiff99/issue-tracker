# Issue 0041: k3s Cutover Polish Before The First Real Run

Status: in-progress
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

- [ ] NB1: `restore.sh` no longer has `|| true` on the scale-to-0 or on the pod wait; only a missing Deployment is tolerated. Proven in kind: an app pod held by a finalizer aborts the restore before any restore Job (and so before any safety dump or restore) is created.
- [ ] NB2: `k3s.md` "What a deploy does" step 3 says a GitHub cancel probably doesn't run the cleanup, that the safe outcome is the app at 0 with the migrate Job maybe still running, and points to "Found the app at 0 replicas".
- [ ] NB3: both cutover restores in `k3s.md` (12b, 12c) use `--keep-app-down` and say the next deploy brings the app up.
- [ ] NB4: `image.yml` uses the concurrency group `image-<sha>`, so a push-to-main build and a pipeline run for the same commit can't race. The `k3s.md` wording no longer says a digest mismatch happens "only if main moved".
- [ ] NB5: kind case: the migration times out (its pod is blocked by a ResourceQuota), the Jobs are deleted, the version is unchanged, and the app scales back up.
- [ ] CI green on the PR.

## Category Checklists

`IT-6` Deployment And Configuration Drift: Verify compose files, env vars, health checks, explicit migrations, and workflow behavior stay aligned.

## Verification

CI `k8s` job (`deployment/k8s/tests/kind-smoke.sh`); `python -m ruff check . && python -m pytest -q tests`.

## STOP

Stop when every AC passes in CI. Do not reach 192.168.10.x or the real cluster.
