# Sprint 0007: Local Manual UAT Readiness

Status: planned
Recommended model: GPT-5.5 high for sprint planning and closeout; GPT-5.5 medium for routine guide edits.

## Goal

Make the Issue Tracker MVP ready for local manual UAT by proving the local runtime, writing the browser UAT script, preparing reset-safe test data guidance, smoking MCP, and establishing a findings closeout.

## Issue Scope

| Issue | Title | Model | Exit condition |
|---|---|---|---|
| Issue 0008 | Local Runtime Gate For Manual UAT | GPT-5.5 high | Build, migration, tests, stack startup, and `/health` are verified or blockers are recorded. |
| Issue 0009 | Manual Web UAT Script | GPT-5.5 medium | Human can follow a documented browser path from setup through issue close. |
| Issue 0010 | Demo Data And Reset-Safe UAT Commands | GPT-5.5 high | UAT data setup and reset are deterministic, local-only, and secret-safe. |
| Issue 0011 | MCP Local UAT Smoke | GPT-5.5 high | MCP smoke and compact-output checks pass. |
| Issue 0012 | UAT Findings And Release Decision | GPT-5.5 high | UAT status and follow-up triage are evidence-backed. |

## Sequential Role Review

Project manager: Keep Sprint 0007 limited to local UAT readiness. Do not add GitHub sync, multi-user roles, drag/drop planning, or production deployment.

Engineering manager: Work in dependency order: runtime gate, web UAT script, data/reset, MCP smoke, findings closeout.

Backend engineer: Verify schema, service invariants, migration, import/export, and close metadata before browser testing is called meaningful.

Frontend engineer: Verify the server-rendered pages are styled and usable in a browser, not just route-test green.

DevOps engineer: Keep migrations explicit, Docker/Compose commands container-only, and reset instructions local-only.

QA engineer: Treat each UAT step as pass/fail with expected result, evidence, blocker, and retry fields.

## Validation Gates

```bash
docker compose -f deployment/docker-compose.local.yml config
docker compose -f deployment/docker-compose.local.yml build
docker compose -f deployment/docker-compose.local.yml run --rm app alembic upgrade head
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/
docker compose -f deployment/docker-compose.local.yml run --rm app python -m issue_tracker.mcp.server --smoke
docker compose -f deployment/docker-compose.local.yml up
```

Manual gates:

- Browser reaches `/setup`, `/login`, `/`, project detail, issue detail, and sprint detail pages.
- Browser flow creates a project, category, valid issue, dependency, sprint, sprint membership, and closes an issue with originating LLM.
- Missing acceptance criteria shows inline validation and does not create an issue.
- `/health` reports database connectivity.
- UAT notes are completed under `documentation/uat/`.

## STOP

Stop only after Sprint 0007 says one of:

- Local manual UAT ready.
- Local manual UAT ready with named caveats.
- Local manual UAT not ready, with exact blockers and owner actions.

Do not expand this sprint into production deployment, GitHub issue sync, multi-user auth, drag/drop planning, or full markdown migration.
