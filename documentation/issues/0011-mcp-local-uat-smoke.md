# Issue 0011: MCP Local UAT Smoke

Status: backlog
Recommended model: GPT-5.5 high
Category gates: `IT-1`, `IT-4`, `IT-6`
Sprint: Sprint 0007

## Problem

The web workflow is only half of the MVP. Manual UAT readiness also needs a local MCP smoke path that proves the agent-facing tools are compact, bounded, and backed by the same service layer.

## Scope

- Run the MCP smoke command in the app container.
- Verify the documented tool list matches the implemented tool list.
- Exercise create/search/get/update/dependency/sprint/next-action paths against local data where practical.
- Confirm default list/search outputs do not dump full issue bodies or acceptance criteria.

## Acceptance Criteria

- [ ] `python -m issue_tracker.mcp.server --smoke` returns the expected tool list.
- [ ] MCP guide lists the same tools that the smoke command returns.
- [ ] `issue.search` default output is bounded and compact.
- [ ] `issue.get` returns full acceptance criteria only when full detail is explicitly requested by ID.
- [ ] Mutating tools return IDs, status, and next-step hints without dumping full records.
- [ ] Any MCP failure is recorded with stderr/stdout separation evidence.

## Category Checklists

`IT-1` Tracker State Integrity: Verify project-local sequence allocation, status transitions, dependency cycle rejection, and immutable close metadata.

`IT-4` MCP Contract And Token Discipline: Verify tool schemas, compact default outputs, limit/filter parameters, opt-in detail, and stderr-only logging.

`IT-6` Deployment And Configuration Drift: Verify compose files, env vars, health checks, explicit migrations, and workflow behavior stay aligned.

## Verification Commands

```bash
docker compose -f deployment/docker-compose.local.yml run --rm app python -m issue_tracker.mcp.server --smoke
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/integration/test_mcp_tools.py
```

## STOP

Stop when MCP smoke and compact-output tests pass, or record the exact failed tool and smallest next fix.
