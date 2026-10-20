# Issue 0010: Demo Data And Reset-Safe UAT Commands

Status: done
Recommended model: GPT-5.5 high
Category gates: `IT-1`, `IT-2`, `IT-6`
Sprint: Sprint 0007

## Problem

Manual UAT needs deterministic data setup and reset instructions that do not rely on hidden database mutation or unsafe production-like commands.

## Scope

- Decide whether UAT uses manual data entry only, a seed command, or an import JSON fixture.
- If a fixture is used, keep it secret-free and small.
- Document reset steps using Docker Compose volumes only for local development.
- Make clear that app startup does not auto-drop, truncate, recreate, or silently migrate databases.

## Acceptance Criteria

- [x] UAT data setup path is documented and repeatable.
- [x] Any fixture contains no secrets, password hashes, sessions, environment values, logs, dumps, or backups.
- [x] Reset instructions are explicitly local-only and cannot be mistaken for deployment guidance.
- [x] Import path requires explicit project and category mapping when source categories are present.
- [x] Shared `NNNN` issue/sprint sequence behavior is visible in the UAT data.

## Evidence (2026-10-20, `a98b164`)

Decision: seed command, no committed fixture. `issue-tracker seed-demo [--project-name NAME]`
(`src/issue_tracker/demo_data.py`, one `cli.py` hook) creates one project through the service layer;
re-running with an existing name is a no-op; it never deletes, truncates, or migrates.

- Seed on compose Postgres → issues `0001`–`0003`, sprint `0004`, issue `0005` (shared sequence), dependency, sprint membership, closed issue with LLM, issue-log entry. Re-run → `{"created": false, ...}`.
- `tests/integration/test_demo_data.py` → 4 passed (deterministic IDs, no-op rerun, other projects untouched, export has no `password`/`APP_SECRET_KEY`/`session`/`DATABASE_URL`).
- `export-json` of the demo → `grep -ciE 'password|secret|session|database_url'` = `0`; `exports/` gitignored.
- `import-json` without `--category-map` → `Import with source categories requires explicit category mapping`, exit 1; with both maps → new project.
- Reset: [`../guides/manual-uat.md#local-reset-local-docker-compose-only`](../guides/manual-uat.md#local-reset-local-docker-compose-only) — boxed as local-machine-only, points cluster data to `k3s.md`/`backup-restore.md`.
- Details: [UAT notes](../uat/2026-10-20-cloud-container-uat-readiness.md). Originating model: claude-opus-5-5 (effort: low).

## Category Checklists

`IT-1` Tracker State Integrity: Verify project-local sequence allocation, status transitions, dependency cycle rejection, and immutable close metadata.

`IT-2` Category And AC Binding: Verify acceptance criteria are required, category checklists are inlined when applicable, and project taxonomies remain project-scoped data.

`IT-6` Deployment And Configuration Drift: Verify compose files, env vars, health checks, explicit migrations, and workflow behavior stay aligned.

## Verification Commands

```bash
docker compose -f deployment/docker-compose.local.yml run --rm app issue-tracker export-json 1 exports/uat-project.json
docker compose -f deployment/docker-compose.local.yml run --rm app issue-tracker import-json exports/uat-project.json UAT-Restored --category-map IT-1=IT-1
```

## STOP

Stop when a reviewer can reset and recreate the UAT data without touching production or committing generated artifacts.
