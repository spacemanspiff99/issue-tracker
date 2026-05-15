from __future__ import annotations

import argparse
import json
import logging
import sys

from issue_tracker.db import SessionLocal
from issue_tracker.mcp import tools

logging.basicConfig(stream=sys.stderr, level=logging.INFO)


def smoke() -> dict[str, object]:
    return {
        "ok": True,
        "tools": [
            "project.list",
            "issue.create",
            "issue.get",
            "issue.search",
            "issue.update_status",
            "issue.add_dependency",
            "sprint.create",
            "sprint.add_issue",
            "sprint.get",
            "category.list",
            "next_action",
        ],
    }


def run_stdio() -> None:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise SystemExit("mcp package is required to run the stdio server") from exc

    mcp = FastMCP("issue-tracker")

    def with_session(fn, *args, **kwargs):
        with SessionLocal() as session:
            return fn(session, *args, **kwargs)

    mcp.tool(name="project.list")(lambda: with_session(tools.project_list))
    mcp.tool(name="issue.create")(lambda project_id, title, acceptance_criteria, category_id=None: with_session(
        tools.issue_create, project_id, title, acceptance_criteria, category_id
    ))
    mcp.tool(name="issue.get")(
        lambda issue_id, include_full=False: with_session(tools.issue_get, issue_id, include_full)
    )
    mcp.tool(name="issue.search")(lambda project_id=None, status=None, limit=20: with_session(
        tools.issue_search, project_id, status, limit
    ))
    mcp.tool(name="issue.update_status")(
        lambda issue_id, status, originating_llm=None, closed_by=None, close_note=None: with_session(
            tools.issue_update_status, issue_id, status, originating_llm, closed_by, close_note
        )
    )
    mcp.tool(name="issue.add_dependency")(
        lambda blocker_issue_id, blocked_issue_id: with_session(
            tools.issue_add_dependency, blocker_issue_id, blocked_issue_id
        )
    )
    mcp.tool(name="sprint.create")(
        lambda project_id, goal, context=None: with_session(tools.sprint_create, project_id, goal, context)
    )
    mcp.tool(name="sprint.add_issue")(
        lambda sprint_id, issue_id: with_session(tools.sprint_add_issue, sprint_id, issue_id)
    )
    mcp.tool(name="sprint.get")(lambda sprint_id: with_session(tools.sprint_get, sprint_id))
    mcp.tool(name="category.list")(lambda project_id: with_session(tools.category_list, project_id))
    mcp.tool(name="next_action")(lambda project_id: with_session(tools.next_action, project_id))
    mcp.run()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    if args.smoke:
        print(json.dumps(smoke(), sort_keys=True))
        return
    run_stdio()


if __name__ == "__main__":
    main()
