# Issue 0010: Demo Data And Reset-Safe UAT Commands

Status: backlog
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

- [ ] UAT data setup path is documented and repeatable.
- [ ] Any fixture contains no secrets, password hashes, sessions, environment values, logs, dumps, or backups.
- [ ] Reset instructions are explicitly local-only and cannot be mistaken for deployment guidance.
- [ ] Import path requires explicit project and category mapping when source categories are present.
- [ ] Shared `NNNN` issue/sprint sequence behavior is visible in the UAT data.

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
