"""End-to-end check of the real stdio MCP server: a client process talks to `python -m issue_tracker.mcp.server`."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from issue_tracker.domain.models import Base
from issue_tracker.services.tracker import IssueService, ProjectService

mcp = pytest.importorskip("mcp")
from mcp import ClientSession, StdioServerParameters  # noqa: E402
from mcp.client.stdio import stdio_client  # noqa: E402

EXPECTED_TOOLS = {
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
}


@pytest.fixture()
def database_url(tmp_path):
    url = f"sqlite+pysqlite:///{tmp_path / 'mcp.db'}"
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        project = ProjectService(session).create_project("Tracker")
        IssueService(session).create_issue(project.id, "Seeded issue", "- [ ] secret-ac-text")
    engine.dispose()
    return url


def _server_env(database_url: str) -> dict[str, str]:
    env = dict(os.environ)
    env.update({"DATABASE_URL": database_url, "APP_SECRET_KEY": "test-only"})
    return env


async def _exercise(database_url: str) -> tuple[set[str], dict]:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "issue_tracker.mcp.server"],
        env=_server_env(database_url),
    )
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        names = {tool.name for tool in (await session.list_tools()).tools}
        result = await session.call_tool("issue.search", {"limit": 5})
        assert not result.isError, result.content
        payload = json.loads(result.content[0].text)
    return names, payload


def test_stdio_server_lists_tools_and_answers_a_call(database_url):
    names, payload = asyncio.run(asyncio.wait_for(_exercise(database_url), timeout=60))

    assert names == EXPECTED_TOOLS
    titles = [issue["title"] for issue in payload["issues"]]
    assert titles == ["Seeded issue"]
    assert "secret-ac-text" not in json.dumps(payload)  # compact by default


def test_stdio_server_writes_only_protocol_frames_to_stdout(database_url):
    init = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "pytest", "version": "0"},
        },
    }
    proc = subprocess.run(
        [sys.executable, "-m", "issue_tracker.mcp.server"],
        input=json.dumps(init) + "\n",
        capture_output=True,
        text=True,
        env=_server_env(database_url),
        timeout=60,
    )

    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    assert lines, proc.stderr
    for line in lines:
        message = json.loads(line)
        assert message.get("jsonrpc") == "2.0"
    assert json.loads(lines[0])["id"] == 1
