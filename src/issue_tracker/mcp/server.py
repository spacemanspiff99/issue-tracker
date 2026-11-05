from __future__ import annotations

import argparse
import json

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


def build_server(session_factory=None):
    """Register every stdio tool. Arguments are always forwarded to ``tools`` by keyword."""
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise SystemExit("mcp package is required to run the stdio server") from exc

    factory = session_factory or SessionLocal
    mcp = FastMCP("issue-tracker")

    def with_session(fn, **kwargs):
        with factory() as session:
            return fn(session, **kwargs)

    mcp.tool(name="project.list")(lambda: with_session(tools.project_list))
    mcp.tool(name="issue.create")(
        lambda project_id, title, acceptance_criteria, category_id=None: with_session(
            tools.issue_create,
            project_id=project_id,
            title=title,
            acceptance_criteria=acceptance_criteria,
            category_id=category_id,
        )
    )
    mcp.tool(name="issue.get")(
        lambda issue_id, include_full=False: with_session(
            tools.issue_get, issue_id=issue_id, include_full=include_full
        )
    )
    mcp.tool(name="issue.search")(
        lambda project_id=None,
        status=None,
        workflow_state=None,
        limit=20,
        view="all",
        query="",
        milestone="",
        unscheduled=False: with_session(
            tools.issue_search,
            project_id=project_id,
            status=status,
            workflow_state=workflow_state,
            limit=limit,
            view=view,
            query=query,
            milestone=milestone,
            unscheduled=unscheduled,
        )
    )
    mcp.tool(name="issue.update_status")(
        lambda issue_id, status, originating_llm=None, closed_by=None, close_note=None: with_session(
            tools.issue_update_status,
            issue_id=issue_id,
            status=status,
            originating_llm=originating_llm,
            closed_by=closed_by,
            close_note=close_note,
        )
    )
    mcp.tool(name="issue.add_dependency")(
        lambda blocker_issue_id, blocked_issue_id: with_session(
            tools.issue_add_dependency, blocker_issue_id=blocker_issue_id, blocked_issue_id=blocked_issue_id
        )
    )
    mcp.tool(name="sprint.create")(
        lambda project_id, goal, context=None: with_session(
            tools.sprint_create, project_id=project_id, goal=goal, context=context
        )
    )
    mcp.tool(name="sprint.add_issue")(
        lambda sprint_id, issue_id: with_session(tools.sprint_add_issue, sprint_id=sprint_id, issue_id=issue_id)
    )
    mcp.tool(name="sprint.get")(lambda sprint_id: with_session(tools.sprint_get, sprint_id=sprint_id))
    mcp.tool(name="category.list")(lambda project_id: with_session(tools.category_list, project_id=project_id))
    mcp.tool(name="next_action")(lambda project_id: with_session(tools.next_action, project_id=project_id))
    mcp.tool(name="guidance_sync.health")(
        lambda project_id: with_session(tools.guidance_sync_health, project_id=project_id)
    )
    mcp.tool(name="guidance_sync.drift_list")(
        lambda project_id, limit=20: with_session(tools.guidance_sync_drift_list, project_id=project_id, limit=limit)
    )
    mcp.tool(name="guidance_sync.create_proposal")(
        lambda project_id, drift_id, action, issue_id, owner, verification_command: with_session(
            tools.guidance_sync_create_proposal,
            project_id=project_id,
            drift_id=drift_id,
            action=action,
            issue_id=issue_id,
            owner=owner,
            verification_command=verification_command,
        )
    )
    mcp.tool(name="backup.health")(lambda project_id: with_session(tools.backup_health, project_id=project_id))
    mcp.tool(name="backup.vibecoding_plan")(
        lambda project_id: with_session(tools.backup_vibecoding_plan, project_id=project_id)
    )
    mcp.tool(name="backup.artifact_check")(
        lambda artifact_names, backend="restic": with_session(
            tools.backup_artifact_check, artifact_names=artifact_names, backend=backend
        )
    )
    mcp.tool(name="rule.resolve")(
        lambda project_types, changed_paths=None, risk_labels=None, include_full=False: with_session(
            tools.rule_resolve,
            project_types=project_types,
            changed_paths=changed_paths,
            risk_labels=risk_labels,
            include_full=include_full,
        )
    )
    mcp.tool(name="prompt.lint")(
        lambda prompt_text, project_types, changed_paths=None, risk_labels=None: with_session(
            tools.prompt_lint,
            prompt_text=prompt_text,
            project_types=project_types,
            changed_paths=changed_paths,
            risk_labels=risk_labels,
        )
    )
    mcp.tool(name="sync.next_actions")(
        lambda project_types: with_session(tools.sync_next_actions, project_types=project_types)
    )
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
