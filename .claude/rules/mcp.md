---
paths:
  - "src/issue_tracker/mcp/**"
  - "tests/integration/test_mcp_tools.py"
---

# MCP invariants (IT-4)

- `tools.py` holds pure functions over a `Session` that call services; `server.py` only registers
  them. No lifecycle logic in either.
- Tool names: ASCII letters, digits, `_`, `-`, `.` (e.g. `issue.get`).
- List/search tools take `limit` (bounded) and filters; return `compact_issue` shapes.
- Full text/AC only when explicitly requested (`include_full=True`).
- Nothing on stdout except protocol; logging goes to stderr.
- Keep `documentation/guides/mcp.md` tool list in sync. Procedure: `mcp-contract` skill.
