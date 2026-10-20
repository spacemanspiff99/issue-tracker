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

Runtime-agnostic: run these wherever the app image runs against a migrated database (local
Compose shown; for k3s run the same commands in an app pod, see [`k3s.md`](k3s.md)).

```bash
C="docker compose -f deployment/docker-compose.local.yml"
$C run --rm app python -m issue_tracker.mcp.server --smoke          # static tool-name list, no DB
$C run --rm app python -m pytest tests/integration/test_mcp_tools.py   # compact-output behavior
$C run --rm app issue-tracker seed-demo                              # data for the stdio check
```

`--smoke` only proves the names are registered; it does not start the stdio server. Prove the
real server with an initialize + `tools/list` + `tools/call` over stdio, keeping stdout and stderr
apart:

```bash
printf '%s\n' \
 '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"uat","version":"0"}}}' \
 '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
 '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
 '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"issue.search","arguments":{"project_id":1}}}' \
 | (cat; sleep 5) | $C run --rm -T app python -m issue_tracker.mcp.server >mcp.out 2>mcp.err
python -c "import json; [json.loads(l) for l in open('mcp.out')]; print('stdout is pure JSON-RPC')"
```

Expected: three JSON-RPC responses on stdout (the `tools/list` names equal the list above; the
`issue.search` items carry only `id`, `sequence`, `title`, `status`, `priority`), and all log lines
in `mcp.err`. Use the demo `project_id` printed by `seed-demo`.

Compact-output checks (pass/fail per tool):

- `issue.search`: default `limit=20`, capped at 50; no `acceptance_criteria` key.
- `issue.get`: compact by default; `acceptance_criteria` only with `include_full=true`.
- `issue.create`, `issue.update_status`, `issue.add_dependency`, `sprint.create`,
  `sprint.add_issue`: return ids, display sequence, status (and a `next` hint on create), never the
  AC body.
