# Issue 0039: Harden The k3s Deploy And Restore Path Before The First Real-Cluster Run

Status: in-progress
Recommended model: claude-opus-5-5 high
Category gates: `IT-6`, `IT-3`
Sprint: Sprint 0007

## Context

An independent re-review of Issue 0020 (PR #13, merged as `5a7db65`) found these gaps in the k3s
pipeline, `deploy.sh`, `restore.sh` and `documentation/guides/k3s.md`. They must be fixed before the
owner's first real-cluster run.

## Files in scope

`deployment/k8s/` (scripts, manifests, tests), `.github/workflows/image.yml`,
`.github/workflows/k3s-pipeline.yml`, the `k8s` job in `.github/workflows/ci.yml`,
`documentation/guides/k3s.md`, this file.

## Acceptance Criteria

- [ ] N1: `deploy-prod` itself fails unless `github.ref == refs/heads/main`, and does not rely only on the environment branch rule.
- [ ] NB1: on timeout, `restore.sh` deletes the restore Job and leaves the app at 0 with a clear message. It never prints "unchanged" while the Job may still commit. Proven in kind.
- [ ] NB2: `--require-empty` passes when `projects` is absent and when it is empty, and refuses when it has rows. All three branches are proven in kind.
- [ ] NB3: the restore takes a safety `pg_dump` of the current DB before dropping the schema, and `deploy.sh` refuses while a `component=restore` Job is active. Proven in kind.
- [ ] NB4: `k3s.md` keeps the kubeconfigs (0600 under `~/.kube/`) for the later steps that need them, and every step uses the same paths.
- [ ] NB5: the production cutover (12c) is checked to use the same commit and digest as the UAT rehearsal (12b).
- [ ] NB6: the write window between backup and rollout is closed or explained.
- [ ] NB7: UAT deploys only from `main`, unless an explicit input is set.
- [ ] NB8: every Postgres image in `deployment/k8s` is pinned to a minor version.
- [ ] CI green on the PR.

## Category Checklists

`IT-6` Deployment And Configuration Drift: Verify compose files, env vars, health checks, explicit migrations, and workflow behavior stay aligned.
`IT-3` Schema And Migration Safety: Verify SQLAlchemy models, PostgreSQL constraints, and Alembic migrations agree; run migration checks on an empty database.

## Verification

```bash
python -m ruff check . && python -m pytest -q tests
python3 deployment/k8s/tests/pipeline-gates.py
# CI `k8s` job: render + kubeconform, digest renders, postgres pin guard, kind-smoke.sh
```

## STOP

Stop when every AC passes in CI on a disposable kind cluster. Do not reach 192.168.10.x or the real
cluster. Out of scope here: the `schema` CI job's `postgres:16` service, and
`docker-compose.local.yml`'s `postgres:16-alpine`. Both are other lanes' files.
