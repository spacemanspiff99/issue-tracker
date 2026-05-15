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
