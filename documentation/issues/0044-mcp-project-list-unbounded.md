# Issue 0044: MCP `project.list` Has No Limit

Status: backlog
Recommended model: claude-opus-5-5 medium
Category gates: `IT-4`
Sprint: Sprint 0007

## Context

Found by issue 0011 UAT on 2026-10-20 (commit `a98b164`). `project.list` takes no arguments and
returns every project; with ~20 projects the default response was 1,508 bytes, already the
largest default output of any tool. The `mcp-contract` skill requires list tools to accept a
bounded `limit`. Low severity for a single-user tracker, but it grows without bound.

## Files in scope

`src/issue_tracker/mcp/tools.py`, `src/issue_tracker/mcp/server.py`, service/repository list
method, `tests/integration/test_mcp_tools.py`, `documentation/guides/mcp.md`.

## Acceptance Criteria

- [ ] `project.list` accepts `limit` (default 20, capped at 50 like `issue.search`) and echoes the effective limit.
- [ ] A test seeds more than the cap and asserts the response length is capped.
- [ ] A test seeds 55 issues and asserts `issue.search(limit=500)` returns 50 (the existing clamp has no test).
- [ ] `--smoke` tool list unchanged.

## Category Checklists

`IT-4` MCP Contract And Token Discipline: Verify tool schemas, compact default outputs, limit/filter parameters, opt-in detail, and stderr-only logging.

## Verification Commands

```bash
python -m pytest -q tests/integration/test_mcp_tools.py
python -m issue_tracker.mcp.server --smoke
```

## STOP

Stop when the capped test passes.
