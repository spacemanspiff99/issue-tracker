# Issue Tracker

Personal issue tracker project for replacing repo-local markdown trackers with one Python service:

- FastAPI and Jinja for a server-rendered web UI.
- SQLAlchemy 2.x, Alembic, and PostgreSQL for durable tracker state.
- A stdio MCP server backed by the same service layer as the web app.

## MVP Runtime

The MVP implementation lives under `src/issue_tracker/` and includes:

- A FastAPI/Jinja web app with first-run setup, login, projects, categories, issues, dependencies, sprints, close metadata, and issue-log viewing.
- SQLAlchemy 2.x models, repository helpers, Alembic migration `0001_initial`, and service-layer invariants shared by web and MCP tools.
- Compact MCP tool adapters under `src/issue_tracker/mcp/`.
- JSON import/export commands that avoid secrets and require explicit category mapping when imported data has source categories.
- Docker Compose files for local app plus PostgreSQL and app-only external PostgreSQL deployment.

## Local Development

Normal development uses Docker/Compose rather than host Python, host virtualenvs, host PostgreSQL, or host Alembic:

```bash
docker compose -f deployment/docker-compose.local.yml build
docker compose -f deployment/docker-compose.local.yml run --rm app alembic upgrade head
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/
docker compose -f deployment/docker-compose.local.yml up
```

The web app runs at `http://localhost:8000`. Visit `/setup` on a fresh database to create the one admin user.

## Useful Commands

```bash
docker compose -f deployment/docker-compose.local.yml run --rm app python -m issue_tracker.mcp.server --smoke
docker compose -f deployment/docker-compose.local.yml run --rm app issue-tracker export-json 1 exports/project-1.json
docker compose -f deployment/docker-compose.local.yml run --rm app issue-tracker import-json exports/project-1.json Imported --category-map IT-1=IT-1
```

Project planning remains in `documentation/planning/PROJECT_PLAN.md`; recurring issue categories remain in `documentation/standards/ISSUE_LOG.md`.

Current planning additions:

- `documentation/planning/EXTERNAL_RULE_REVIEW.md` records the GitHub rule review and GPT-5.5 medium/high guidance changes.
- `documentation/guides/manual-uat.md` is the browser and command checklist for local manual UAT.
- `documentation/uat/TEMPLATE-local-uat.md` is the notes template for a UAT run.
- `documentation/sprints/0007-local-manual-uat-readiness.md` is the next sprint to get the MVP ready for local manual UAT.
- `documentation/sprints/0008-subagent-local-uat-quality-iteration.md` decomposes the local UAT push into subagent-sized worker scopes.
- `documentation/issues/0008-local-runtime-gate.md` through `documentation/issues/0012-uat-findings-and-release-decision.md` are the sprint issues.
