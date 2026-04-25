# Issue Tracker

Personal issue tracker project for replacing repo-local markdown trackers with one Python service:

- FastAPI and Jinja for a server-rendered web UI.
- SQLAlchemy 2.x, Alembic, and PostgreSQL for durable tracker state.
- A stdio MCP server backed by the same service layer as the web app.

## Current State

This repository currently contains the project rules, recurring issue taxonomy, mirror workflow, and MVP plan.

Start with:

- `documentation/planning/PROJECT_PLAN.md` for architecture and sprint plan.
- `.cursor/rules/core.mdc` for project invariants.
- `documentation/standards/ISSUE_LOG.md` for this project's recurring issue categories.

Implementation should follow the sprint order in the project plan and stop after each sprint's validation gates pass.
