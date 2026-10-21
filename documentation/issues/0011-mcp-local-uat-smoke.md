# Issue 0011: MCP Local UAT Smoke

Status: in-progress — dev-path (Compose) AC pass at `cac4a09`; k3s UAT AC marked OWNER are open.
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

Smoke steps: [`../guides/mcp.md#uat-smoke`](../guides/mcp.md#uat-smoke) (k3s UAT target, Compose as dev rehearsal).

- [x] `python -m issue_tracker.mcp.server --smoke` returns the expected tool list → compose app container, `cac4a09`: `{"ok": true, "tools": [11 names]}`.
- [x] MCP guide lists the same tools that the smoke command returns → the guide's "Tool set" list equals the smoke list in order (scripted compare: `True 11`).
- [x] `issue.search` default output is bounded and compact → live on the demo project (`cac4a09`): 449 B, items keys `id, priority, sequence, status, title`, no `acceptance_criteria`; `limit=500` → effective `limit: 50`. `tests/integration/test_mcp_tools.py` → `4 passed`.
- [x] `issue.get` returns full acceptance criteria only when full detail is explicitly requested by ID → 115 B compact without AC; 265 B with `include_full=True`, AC present.
- [x] Mutating tools return IDs, status, and next-step hints without dumping full records → asserted in `test_mcp_tools.py` (passing at `cac4a09`).
- [x] Any MCP failure is recorded with stderr/stdout separation evidence → stdio initialize/`tools/list`/`tools/call` on the `cac4a09` image (mcp `2.3.0`): stdout `0` lines, stderr `mcp package is required to run the stdio server`. Fix tracked in [0043](0043-mcp-2x-breaks-stdio-server.md); `project.list` unbounded → [0044](0044-mcp-project-list-unbounded.md). This blocks the 0012 release decision.
- [ ] **OWNER** — On UAT (`K="kubectl -n issue-tracker-uat"`): `$K exec deploy/issue-tracker -- python -m issue_tracker.mcp.server --smoke` → the same 11 names; `$K exec deploy/issue-tracker -- python -m pytest -q -p no:cacheprovider tests/integration/test_mcp_tools.py` → `4 passed`; stdio script from the guide → until 0043 merges, expect stdout empty + the stderr line above (record as Fail); after 0043, three JSON-RPC lines on stdout and logs only in `mcp.err`.

Originating model: claude-opus-5-5 (effort: medium).

## Category Checklists

`IT-1` Tracker State Integrity: Verify project-local sequence allocation, status transitions, dependency cycle rejection, and immutable close metadata.

`IT-4` MCP Contract And Token Discipline: Verify tool schemas, compact default outputs, limit/filter parameters, opt-in detail, and stderr-only logging.

`IT-6` Deployment And Configuration Drift: Verify compose files, env vars, health checks, explicit migrations, and workflow behavior stay aligned.

## Verification Commands

```bash
K="kubectl -n issue-tracker-uat"                                    # owner, UAT
$K exec deploy/issue-tracker -- python -m issue_tracker.mcp.server --smoke
$K exec deploy/issue-tracker -- python -m pytest -q -p no:cacheprovider tests/integration/test_mcp_tools.py
docker compose -f deployment/docker-compose.local.yml run --rm app python -m issue_tracker.mcp.server --smoke   # dev path
```

## STOP

Stop when MCP smoke and compact-output tests pass, or record the exact failed tool and smallest next fix.
