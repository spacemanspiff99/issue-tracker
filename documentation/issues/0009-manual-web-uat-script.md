# Issue 0009: Manual Web UAT Script

Status: backlog
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

- [ ] Manual UAT guide names the exact local URL and startup prerequisites.
- [ ] Guide includes setup/login path and expected session-cookie behavior at a high level without exposing secrets.
- [ ] Guide proves creating an issue without acceptance criteria shows validation and does not create a row.
- [ ] Guide covers project, category, issue, dependency, sprint, sprint assignment, close metadata, and issue-log viewing.
- [ ] Guide includes a page styling sanity check for each main page.
- [ ] Guide includes a UAT notes template with pass/fail, blocker, evidence, and retry fields.

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
