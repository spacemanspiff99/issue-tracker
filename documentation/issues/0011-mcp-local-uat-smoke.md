# Issue 0011: MCP Local UAT Smoke

Status: done
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

- [x] `python -m issue_tracker.mcp.server --smoke` returns the expected tool list.
- [x] MCP guide lists the same tools that the smoke command returns.
- [x] `issue.search` default output is bounded and compact.
- [x] `issue.get` returns full acceptance criteria only when full detail is explicitly requested by ID.
- [x] Mutating tools return IDs, status, and next-step hints without dumping full records.
- [x] Any MCP failure is recorded with stderr/stdout separation evidence.

## Evidence (2026-10-20, `a98b164`, compose app container)

- `--smoke` → `{"ok": true, "tools": [11 names]}`; `diff` against the list in `documentation/guides/mcp.md` is empty.
- `pytest tests/integration/test_mcp_tools.py` → `3 passed`.
- Live tool calls on the seeded demo project: `issue.search` default 449 B (5 compact keys, no AC), `limit=500` → effective limit 50; `issue.get` 115 B compact, AC only with `include_full=true` (265 B); `issue.create`/`update_status`/`sprint.create`/`sprint.add_issue` 77–177 B, ids + status (+ `next` hint on create), no AC body.
- **Failure recorded:** the stdio server does not start on a fresh build (mcp 2.x removed `FastMCP`): stdout 0 lines, stderr `mcp package is required to run the stdio server`. With `mcp<2` in a throwaway container: stdout = 3 JSON-RPC lines, logs on stderr only. Smallest fix → [0025](0025-mcp-2x-breaks-stdio-server.md). `project.list` unbounded → [0026](0026-mcp-project-list-unbounded.md).
- Stdio smoke script added to [`../guides/mcp.md#uat-smoke`](../guides/mcp.md#uat-smoke). Details: [UAT notes](../uat/2026-10-20-cloud-container-uat-readiness.md).
- Originating model: claude-opus-5-5 (effort: low). This issue's AC pass; the stdio blocker is carried by 0025 and blocks the 0012 release decision.

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
