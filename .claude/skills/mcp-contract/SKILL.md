---
name: mcp-contract
description: Use when adding, renaming, or changing an MCP tool in `src/issue_tracker/mcp/` — its arguments, defaults, output shape, or logging — or when updating `documentation/guides/mcp.md`. Covers IT-4 (tool schemas, compact default output, bounded lists, opt-in detail, stderr-only logging) and the smoke check.
---

# MCP Contract (IT-4)

## Adding or changing a tool

1. Service method exists and is tested (`tracker-invariants`).
2. Pure function in `mcp/tools.py`: `(session, ...) -> dict`, returns `compact_issue(...)` /
   small dicts with ids, status, display id, and a next-step hint. No full AC/text unless
   `include_full=True`.
3. Register in `server.py` `run_stdio()` via `with_session`, and add the name to the static
   list in `smoke()` (asserted by `test_mcp_smoke_lists_expected_tools`).
4. Lists: accept `limit` (service bounds it), `status`, `project_id`.
5. Update the tool list in `documentation/guides/mcp.md` and the tool list in
   `documentation/planning/PROJECT_PLAN.md` "MCP Server Design" if the set changed.

## Verify

```bash
python -m pytest -q tests/integration/test_mcp_tools.py
python -m issue_tracker.mcp.server --smoke     # static tool-name list; no DB needed
```

`--smoke` only proves registration names; behavior proof is the test. Test asserts: output keys (no full-text keys by default), `limit` honored, a mutation returns ids
not records. If you touched logging, assert nothing non-protocol reaches stdout.

Token budget: a list call with default args should be a few hundred tokens, not thousands. If a
response grows, add a filter or opt-in flag rather than truncating silently.
