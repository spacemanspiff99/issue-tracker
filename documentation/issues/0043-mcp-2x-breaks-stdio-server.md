# Issue 0043: MCP Stdio Server Fails To Start With mcp 2.x

Status: backlog
Recommended model: claude-opus-5-5 high
Category gates: `IT-4`, `IT-6`
Sprint: Sprint 0007

## Context

Found by issue 0011 UAT on 2026-10-20 (commit `a98b164`). `pyproject.toml` pins `mcp>=1.2`, so a
fresh image installs mcp 2.x, where `mcp.server.fastmcp.FastMCP` was removed. `run_stdio()`
then exits with `mcp package is required to run the stdio server` and writes nothing to stdout.
`--smoke` and `tests/integration/test_mcp_tools.py` stay green because neither imports the SDK,
so CI cannot see this. Evidence (fresh `deployment-app` image):

```text
$ python -c "from mcp.server.fastmcp import FastMCP"
ModuleNotFoundError: No module named 'mcp.server.fastmcp'. This is mcp 2.x, where FastMCP was
renamed to MCPServer ... or pin 'mcp<2' to keep running v1 code.
$ (initialize; tools/list; tools/call) | python -m issue_tracker.mcp.server
stdout: 0 lines   stderr: mcp package is required to run the stdio server
```

Same stdio script after `pip install 'mcp<2'` (1.30.0) in a throwaway container: stdout = 3
JSON-RPC responses (initialize, 11 tools, compact `issue.search`), INFO logs on stderr only.

## Files in scope

`pyproject.toml` (pin `mcp>=1.2,<2`, or port `run_stdio()` to `MCPServer`), `src/issue_tracker/mcp/server.py`,
`tests/integration/test_mcp_tools.py`.

## Acceptance Criteria

- [ ] A fresh image build starts the stdio server: the initialize + `tools/list` + `tools/call issue.search` script in `documentation/guides/mcp.md#uat-smoke` returns 3 JSON-RPC lines on stdout.
- [ ] A test imports the SDK server class used by `run_stdio()` and builds the server (no network), so a breaking SDK upgrade fails CI.
- [ ] stdout carries only JSON-RPC; logs stay on stderr.

## Category Checklists

`IT-4` MCP Contract And Token Discipline: Verify tool schemas, compact default outputs, limit/filter parameters, opt-in detail, and stderr-only logging.

`IT-6` Deployment And Configuration Drift: Verify compose files, env vars, health checks, explicit migrations, and workflow behavior stay aligned.

## Verification Commands

```bash
docker compose -f deployment/docker-compose.local.yml build
python -m pytest -q tests/integration/test_mcp_tools.py
# plus the stdio script in documentation/guides/mcp.md#uat-smoke
```

## STOP

Stop when the stdio script passes on a fresh build, or record the SDK version and the failing import.
