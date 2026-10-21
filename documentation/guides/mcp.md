# MCP Guide

The MVP exposes compact stdio MCP tools backed by the same services used by the web routes.

Smoke check:

```bash
docker compose -f deployment/docker-compose.local.yml run --rm app python -m issue_tracker.mcp.server --smoke
```

Tool set:

- `project.list`
- `issue.create`
- `issue.get`
- `issue.search`
- `issue.update_status`
- `issue.add_dependency`
- `sprint.create`
- `sprint.add_issue`
- `sprint.get`
- `category.list`
- `next_action`

List and search outputs are bounded and compact by default. Full issue content and acceptance criteria are returned only from `issue.get` when full detail is explicitly requested.

Stdio logs are configured for stderr so protocol output is not polluted.

## UAT smoke

Target: the k3s UAT namespace `issue-tracker-uat` ([`k3s.md`](k3s.md)), run from the owner machine.
Local Compose is the dev rehearsal of the same steps (`K` replaced by
`docker compose -f deployment/docker-compose.local.yml run --rm -T app`). Never point an MCP UAT
at the production namespace `issue-tracker`.

```bash
K="kubectl -n issue-tracker-uat"
$K exec deploy/issue-tracker -- python -m issue_tracker.mcp.server --smoke          # static tool-name list, no DB
$K exec deploy/issue-tracker -- python -m pytest -q -p no:cacheprovider tests/integration/test_mcp_tools.py  # compact-output behavior (in-memory SQLite)
$K exec deploy/issue-tracker -- issue-tracker seed-demo                              # data for the stdio check; refuses production
```

Expected: `{"ok": true, "tools": [...]}` with exactly the tool set above; `4 passed`; the
`seed-demo` JSON (note its `project_id`).

`--smoke` only proves the names are registered; it does not start the stdio server. Prove the
real server with an initialize + `tools/list` + `tools/call` over stdio, keeping stdout and stderr
apart (replace `1` with the demo `project_id`):

```bash
printf '%s\n' \
 '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"uat","version":"0"}}}' \
 '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
 '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
 '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"issue.search","arguments":{"project_id":1}}}' \
 | (cat; sleep 5) | $K exec -i deploy/issue-tracker -- python -m issue_tracker.mcp.server >mcp.out 2>mcp.err
python3 -c "import json; [json.loads(l) for l in open('mcp.out')]; print('stdout is pure JSON-RPC')"
```

Expected: three JSON-RPC responses on stdout (the `tools/list` names equal the list above; the
`issue.search` items carry only `id`, `sequence`, `title`, `status`, `priority`), and all log lines
in `mcp.err`. Until [0043](../issues/0043-mcp-2x-breaks-stdio-server.md) is fixed, a fresh image
installs mcp 2.x and this fails with stdout empty and `mcp package is required to run the stdio
server` on stderr; record that as the result, not a pass. The stdio server opens its own DB
session: close it before any UAT reset (`restore.sh`).

Compact-output checks (pass/fail per tool):

- `issue.search`: default `limit=20`, capped at 50; no `acceptance_criteria` key.
- `issue.get`: compact by default; `acceptance_criteria` only with `include_full=true`.
- `issue.create`, `issue.update_status`, `issue.add_dependency`, `sprint.create`,
  `sprint.add_issue`: return ids, display sequence, status (and a `next` hint on create), never the
  AC body.
