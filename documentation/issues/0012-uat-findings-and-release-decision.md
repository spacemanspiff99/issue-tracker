# Issue 0012: UAT Findings And Release Decision

Status: backlog
Recommended model: GPT-5.5 high
Category gates: `IT-1`, `IT-4`, `IT-5`, `IT-6`
Sprint: Sprint 0007

## Problem

Manual UAT needs a controlled closeout so defects become follow-up issues instead of ambiguous notes, and so the project is not called ready without evidence.

## Scope

- Add a UAT findings template.
- Record environment, commit SHA, browser, commands run, pass/fail status, screenshots or notes paths, and blockers.
- Triage findings into must-fix-before-UAT, can-fix-after-UAT, and non-MVP backlog.
- Make the release decision explicit: ready for local manual UAT, not ready, or ready with named caveats.

## Acceptance Criteria

- [ ] UAT notes template exists under `documentation/uat/`.
- [ ] Template records commit SHA, environment, browser, commands, tester, date, and pass/fail.
- [ ] Template has sections for web workflow, MCP workflow, import/export, reset, and known blockers.
- [ ] Every failed UAT step maps to a follow-up issue or an explicit non-MVP backlog item.
- [ ] Sprint 0007 closeout states whether local manual UAT is ready, not ready, or ready with caveats.

## Category Checklists

`IT-1` Tracker State Integrity: Verify project-local sequence allocation, status transitions, dependency cycle rejection, and immutable close metadata.

`IT-4` MCP Contract And Token Discipline: Verify tool schemas, compact default outputs, limit/filter parameters, opt-in detail, and stderr-only logging.

`IT-5` Auth And Secret Safety: Verify password hashing, session flags, setup flow, secret handling, and no credential logging.

`IT-6` Deployment And Configuration Drift: Verify compose files, env vars, health checks, explicit migrations, and workflow behavior stay aligned.

## Verification Commands

```bash
git status --short --branch
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/
```

## STOP

Stop when Sprint 0007 has evidence-backed UAT status and every blocker has an owner action or follow-up issue.
