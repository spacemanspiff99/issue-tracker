# Web UI Modernization Decisions

Sprint 0043 keeps the Issue Tracker web UI server-rendered with FastAPI, Jinja, and regular HTML forms. The app should remain useful without a frontend build step.

## Decisions

- Navigation stays project-centered: project detail links to saved views, backlog, board, planning, and backup surfaces.
- Saved issue views are bookmarkable query-string routes over service-layer filters: all, backlog, active sprint, blocked, done, and uncategorized.
- Inline issue edits use normal POST forms and redirects. Status, priority, planning metadata, comments, and GitHub references all flow through `IssueService`.
- Planning metadata uses the existing `Issue.labels` JSON field for labels, story, delivery phase, milestone, custom fields, and backlog rank. This avoids a schema migration while the workflow is still dogfooding.
- Comments and recent activity reuse `IssueEvent`.
- GitHub references reuse `LinkedPR` as reference-only metadata. Full sync is intentionally out of scope.
- Category governance remains project-scoped. The recommended tracker taxonomy is created only on request for a project.
- Backup and markdown planning surfaces point users to existing safe CLI/documentation workflows. They do not create committed exports or dumps.

## Verification

The route and service surfaces are covered by:

```bash
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/
docker compose -f deployment/docker-compose.local.yml run --rm app python -m ruff check --no-cache .
```

Browser-level desktop and mobile UAT still requires a browser-capable environment and should follow `documentation/guides/manual-uat.md`.
