from __future__ import annotations

import argparse
import inspect
import json
import typing

from issue_tracker.config import get_settings
from issue_tracker.db import SessionLocal
from issue_tracker.logging import configure_logging
from issue_tracker.mcp import tools

configure_logging(get_settings(), service="mcp")


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
            "guidance_sync.health",
            "guidance_sync.drift_list",
            "guidance_sync.create_proposal",
            "backup.health",
            "backup.vibecoding_plan",
            "backup.artifact_check",
            "rule.resolve",
            "prompt.lint",
            "sync.next_actions",
        ],
    }


def _session_tool(factory, fn):
    """Wrap ``fn(session, **kwargs)`` as an MCP tool that opens its own session.

    The wrapper publishes ``fn``'s resolved type hints (minus ``session``) so FastMCP
    validates and coerces arguments (for example ``"1"`` -> ``1`` for integer IDs).
    Untyped wrappers made every argument a string, which PostgreSQL rejects when
    compared with integer columns. No return annotation is published, so the
    tool output contract stays unchanged.
    """
    hints = typing.get_type_hints(fn)
    params = [
        param.replace(annotation=hints.get(param.name, inspect.Parameter.empty))
        for param in inspect.signature(fn).parameters.values()
        if param.name != "session"
    ]

    def tool(**kwargs):
        with factory() as session:
            return fn(session, **kwargs)

    tool.__name__ = fn.__name__
    tool.__doc__ = fn.__doc__
    tool.__signature__ = inspect.Signature(params)
    return tool


def build_server(session_factory=None):
    """Register every stdio tool. Arguments are always forwarded to ``tools`` by keyword."""
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise SystemExit("mcp package is required to run the stdio server") from exc

    factory = session_factory or SessionLocal
    mcp = FastMCP("issue-tracker")

    for name in smoke()["tools"]:
        mcp.tool(name=name)(_session_tool(factory, getattr(tools, name.replace(".", "_"))))
    return mcp


def run_stdio() -> None:
    build_server().run()


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
