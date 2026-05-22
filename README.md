# Issue Tracker

Personal issue tracker project for replacing repo-local markdown trackers with one Python service:

- FastAPI and Jinja for a server-rendered web UI.
- SQLAlchemy 2.x, Alembic, and PostgreSQL for durable tracker state.
- A stdio MCP server backed by the same service layer as the web app.

## MVP Runtime

The MVP implementation lives under `src/issue_tracker/` and includes:

- A FastAPI/Jinja web app with first-run setup, login, projects, categories, issues, dependencies, sprints, close metadata, and issue-log viewing.
- SQLAlchemy 2.x models, repository helpers, Alembic migrations through `0003_guidance_audit_events`, and service-layer invariants shared by web and MCP tools.
- Compact MCP tool adapters under `src/issue_tracker/mcp/`.
- JSON import/export commands that avoid secrets and require explicit category mapping when imported data has source categories.
- Docker Compose files for local app plus PostgreSQL and app-only external PostgreSQL deployment.
- Guidance Sync models, services, dashboard, audit records, event ingestion, dry-run proposal execution, rollback planning, and compact MCP tools for branch-aware AI guidance drift work.

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

- `documentation/guides/deployment.md` includes the local GitHub Actions runner pipeline for UAT at `192.168.10.26` and production at `192.168.10.27`.
- `documentation/guides/comprehensive-test-plan.md` defines the production-safety test gates for backup, restore, Guidance Sync, MCP, migrations, import/export, UAT, and deployment behavior.
- `documentation/guides/product-guide.md` explains the purpose of the software and the current web, voice intake, release, sprint, issue, project, import/export, and MCP functionality.
- `documentation/planning/VIBECODING_RULE_SYNC_PRODUCT_PLAN.md` plans the Guidance Sync product area for keeping child project rules aligned with `vibecoding` across branches.
- `documentation/planning/GUIDANCE_SYNC_BACKUP_AND_RULE_RELEVANCE_BACKLOG.md` expands that plan into portable backups, vibecoding backup targets, rule applicability, critical-rule coverage, and cross-project sync backlog issues.
- `documentation/planning/EXTERNAL_RULE_REVIEW.md` records the GitHub rule review and GPT-5.5 medium/high guidance changes.
- `documentation/guides/manual-uat.md` is the browser and command checklist for local manual UAT.
- `documentation/guides/web-ui-modernization.md` records the Sprint 0043 server-rendered web UI decisions.
- `documentation/uat/TEMPLATE-local-uat.md` is the notes template for a UAT run.
- `documentation/sprints/0007-local-manual-uat-readiness.md` is the next sprint to get the MVP ready for local manual UAT.
- `documentation/sprints/0008-subagent-local-uat-quality-iteration.md` decomposes the local UAT push into subagent-sized worker scopes.
- `documentation/sprints/0043-overnight-modern-web-app-buildout.md` records the dogfood Sprint 0043 modern web app slice and STOP handoff.
- `documentation/sprints/0050-backlog-ux-release-voice-feedback-playwright.md` records the backlog completion sprint for releases, drag/drop, sidebar, voice feedback, and comprehensive Playwright coverage.
- `documentation/sprints/0073-magicpatterns-ui-implementation.md` records the active MagicPatterns UI implementation backlog and sprint.
- `documentation/sprints/0078-sprint-0073-ui-regression-fixes.md` records the corrective sprint for Sprint 0073 UI regressions and the Playwright gate.
- `documentation/sprints/0112-uat-deploy-comprehensive-test-suite.md` records the closed UAT deployment sprint and final UAT evidence.
- `documentation/sprints/0119-production-readiness-comprehensive-test-drill.md` plans the comprehensive production-readiness drill before production-project use.
- `documentation/design/magicpatterns/UI.tsx` preserves the protected MagicPatterns-generated UI source artifact for Sprint 0073.
- `documentation/guides/ai-coding-tracker-ux.md` records the AI-coding-specific UX principles behind the Sprint 0050 workspace changes.
- `documentation/prompts/0043-finish-overnight-modern-web-app-buildout.md` is the fresh-session execution prompt for finishing Sprint 0043.
- `documentation/issues/0008-local-runtime-gate.md` through `documentation/issues/0012-uat-findings-and-release-decision.md` are the sprint issues.
