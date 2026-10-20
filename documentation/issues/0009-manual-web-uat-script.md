# Issue 0009: Manual Web UAT Script

Status: done
Recommended model: GPT-5.5 medium
Category gates: `IT-1`, `IT-2`, `IT-5`, `IT-6`
Sprint: Sprint 0007

## Problem

The project needs a repeatable local manual UAT script that a human can run in the browser without guessing the intended MVP path.

## Scope

- Create or update a manual UAT guide under `documentation/guides/`.
- Cover first-run setup, login, project creation, category creation, issue creation validation, dependency creation, sprint creation, sprint issue assignment, issue close with originating LLM, and issue-log viewing.
- Include expected results, notes fields, and pass/fail recording guidance.
- Include browser styling sanity checks so raw HTML or broken CSS is caught.

## Acceptance Criteria

- [x] Manual UAT guide names the exact local URL and startup prerequisites.
- [x] Guide includes setup/login path and expected session-cookie behavior at a high level without exposing secrets.
- [x] Guide proves creating an issue without acceptance criteria shows validation and does not create a row.
- [x] Guide covers project, category, issue, dependency, sprint, sprint assignment, close metadata, and issue-log viewing.
- [x] Guide includes a page styling sanity check for each main page.
- [x] Guide includes a UAT notes template with pass/fail, blocker, evidence, and retry fields.

## Evidence (2026-10-20, `a98b164`)

- Guide: [`../guides/manual-uat.md`](../guides/manual-uat.md) — base URL `http://localhost:8000` + prerequisites (§1), runtime-agnostic with [`k3s.md`](../guides/k3s.md) for the cluster, one row per catalog workflow (`W-SETUP` … `W-ISSUE-CLOSE`) naming its `tests/e2e` test, cookie flags checked in devtools without copying values, whitespace-only AC error + no row, styling check per page at desktop and phone width, notes template link.
- The guide's path was driven end to end by Playwright on a fresh compose stack: `22 passed` (desktop + mobile). Results: [UAT notes](../uat/2026-10-20-cloud-container-uat-readiness.md).
- Human click-through of the guide is owed by the owner and recorded under issue 0012.
- Originating model: claude-opus-5-5 (effort: low).

## Category Checklists

`IT-1` Tracker State Integrity: Verify project-local sequence allocation, status transitions, dependency cycle rejection, and immutable close metadata.

`IT-2` Category And AC Binding: Verify acceptance criteria are required, category checklists are inlined when applicable, and project taxonomies remain project-scoped data.

`IT-5` Auth And Secret Safety: Verify password hashing, session flags, setup flow, secret handling, and no credential logging.

`IT-6` Deployment And Configuration Drift: Verify compose files, env vars, health checks, explicit migrations, and workflow behavior stay aligned.

## Verification Commands

```bash
docker compose -f deployment/docker-compose.local.yml up
```

Manual browser verification follows the guide.

## STOP

Stop when the guide can be followed from a fresh local stack, or record the first failing step and the evidence needed to debug it.
