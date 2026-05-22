# Prompt: Finish Sprint 0043 Overnight Modern Web App Buildout

Use this prompt in a fresh Codex session. Do not continue in the same session that created or updated this prompt.

## Context

Repository: `/home/akun/issue-tracker`

Sprint 0043 exists in the running local tracker database:

- Sequence: `0043`
- Goal: `Overnight modern web app buildout`
- Status at handoff: active
- Tracker context: `Oversized dogfood sprint loaded for overnight autonomous work. Work high-priority items first, keep Docker verification gates, and leave STOP notes for unfinished slices.`

Durable handoff:

- `documentation/sprints/0043-overnight-modern-web-app-buildout.md`
- `documentation/uat/2026-05-15-sprint-0043-route-and-runtime-uat.md`

The previous pass completed the first modern UI/parity slice and closed tracker issues `0001`, `0002`, `0003`, `0004`, `0005`, `0006`, `0007`, `0009`, `0014`, `0015`, `0016`, `0017`, and `0018` in the local tracker. Sprint 0043 still has 27 active assigned issues.

Important current caveat: browser-level desktop/mobile manual UAT was not run. Route/runtime UAT passed, but the browser UAT evidence remains required before closing browser-facing work.

This prompt is not a next-slice prompt. Its objective is to finish Sprint 0043 end to end. If the work is too large for one uninterrupted pass, keep executing sequentially with phased verification and subagents where useful. Leave a STOP only when Sprint 0043 is complete, a genuine blocker prevents further progress, or the user explicitly accepts named deferrals for remaining issues. Sprint size by itself is not a blocker.

## Required Model And Reasoning

Default to GPT-5.5 medium for normal UI implementation and route tests.

Use GPT-5.5 high for:

- browser/runtime debugging
- auth or session behavior
- schema or migration work
- MCP contract changes
- destructive reset decisions
- sprint closeout

Use lighter reasoning only for small mechanical edits after the implementation direction is proven.

## Start Procedure

1. Read `AGENTS.md`.
2. Read `documentation/sprints/0043-overnight-modern-web-app-buildout.md`.
3. Inspect the current dirty worktree with `git status --short --branch --ignored`.
4. Query the running tracker Sprint 0043 before implementation:

```bash
docker compose -f deployment/docker-compose.local.yml run --rm app python -c "exec('from issue_tracker.db import SessionLocal\nfrom issue_tracker.domain.models import Sprint,SprintIssue,Issue\nfrom sqlalchemy import select\ns=SessionLocal()\nsprint=s.scalar(select(Sprint).where(Sprint.sequence==43))\nprint({\"id\": sprint.id, \"project_id\": sprint.project_id, \"sequence\": sprint.sequence, \"goal\": sprint.goal, \"status\": sprint.status.value})\nrows=s.execute(select(Issue.sequence,Issue.title,Issue.status,SprintIssue.status).join(SprintIssue, SprintIssue.issue_id==Issue.id).where(SprintIssue.sprint_id==sprint.id).order_by(SprintIssue.sort_order, Issue.sequence)).all()\nfor row in rows:\n    print(row)\n')"
```

5. Do not infer completion from markdown alone. Keep the running tracker and durable markdown handoff aligned.

## Files In Scope

Primary UI scope:

- `src/issue_tracker/web/app.py`
- `src/issue_tracker/web/templates/*.html`
- `tests/integration/test_web_routes.py`
- `documentation/guides/manual-uat.md`
- `documentation/uat/`
- `documentation/sprints/0043-overnight-modern-web-app-buildout.md`

Service/repository scope only as needed for the next product slice:

- `src/issue_tracker/services/tracker.py`
- `src/issue_tracker/repositories/store.py`
- `tests/unit/test_services.py`

MCP scope only if a web feature exposes behavior that MCP must share:

- `src/issue_tracker/mcp/`
- `tests/integration/test_mcp_tools.py`
- `documentation/guides/mcp.md`

Avoid schema changes unless the selected next slice proves a schema invariant is required. If schema changes are needed, create a separate Alembic migration and run the explicit migration gate.

## Implementation Order

Finish all remaining Sprint 0043 issues. Work sequentially through the phases below. Use subagents when they materially help, but keep ownership disjoint and do not hand off the immediate blocker on the critical path.

### Phase 0: Browser UAT Gate

Complete issue `0008` first:

1. Start the local stack.
2. Use the browser path in `documentation/guides/manual-uat.md`.
3. Verify desktop and mobile viewport usability for setup/login, project list, project detail, issue detail, sprint detail, validation errors, dependencies, sprint assignment, close metadata, and issue-log view.
4. Record evidence in a dated file under `documentation/uat/`.
5. If browser UAT finds defects, fix must-fix defects before starting feature work.

### Phase 1: Server-Rendered Navigation And Views

Complete these issues in order because later workflow surfaces depend on them:

1. `0019` Add saved issue views for backlog, active sprint, blocked, done, and uncategorized work.
2. `0033` Add sprint and backlog navigation views.
3. `0024` Add blocked indicator and dependency health summary.
4. `0028` Add sprint and project progress summaries.
5. `0027` Add global project search.

Expected implementation shape:

- Bookmarkable server-rendered routes for saved views and search.
- Repository/service helpers for filtering, dependency health, and rollup counts.
- Templates display compact status, category, blocker, and progress metadata without duplicating lifecycle rules.
- Route and service tests cover each helper and at least two route-visible filtered views.

Subagent option: use one explorer for route/template risk and one explorer for repository/service helper shape. Do not use workers in parallel on the same files unless write scopes are explicitly split.

### Phase 2: Editing And Planning Workflows

Complete these issues after Phase 1:

1. `0034` Add issue edit sidebar for single-window editing.
2. `0035` Add inline status and priority dropdowns on issue lists.
3. `0020` Add sortable backlog priority controls.
4. `0023` Add quick issue create and inline edit affordances.

Expected implementation shape:

- Use existing service methods or add service methods where lifecycle behavior is shared by web and MCP.
- Keep status transitions and close metadata invariants in the service layer.
- Use regular forms and server-rendered redirects unless there is an existing local pattern for partial updates.
- Add route tests for edit, inline status/priority update, ordering, and quick create validation.

Subagent option: after service APIs are locally designed, split workers by write scope:

- Worker A owns service/repository/tests for updates and ordering.
- Worker B owns templates/routes/tests for sidebar and quick create.

Workers must not edit each other's files.

### Phase 3: Grouping, Taxonomy, And Rollups

Complete these issues after edit workflows are stable:

1. `0037` Add category governance and recommended base taxonomy.
2. `0039` Add story grouping for complex features.
3. `0040` Add delivery phase field for issue lifecycle planning.
4. `0042` Add story and sprint rollup summaries.
5. `0022` Add roadmap or milestone grouping.
6. `0041` Add story templates for common delivery patterns.

Expected implementation shape:

- Prefer existing JSON fields or service-level conventions where acceptable; use schema changes only when the acceptance criteria cannot be met safely otherwise.
- If schema changes are required, create one Alembic migration for the phase and verify empty-database upgrade.
- Category governance remains project-scoped. Do not hardcode peer project taxonomies.
- Rollup calculations belong in repository/service helpers, not templates.

Subagent option: use high-reasoning worker only if schema/migration work becomes necessary. Otherwise keep implementation local or use medium workers with disjoint files.

### Phase 4: Collaboration, History, And External Reference Surfaces

Complete these issues after grouping fields exist:

1. `0025` Add issue comments or notes timeline.
2. `0026` Add labels and lightweight custom fields.
3. `0029` Add activity feed and recent changes view.
4. `0031` Add GitHub reference fields without full sync.

Expected implementation shape:

- Reuse `IssueEvent`, `labels`, and `LinkedPR` where possible before adding schema.
- Keep GitHub fields as references only; do not implement full sync.
- Add service and route tests for comments/notes, labels/custom fields, activity feed, and linked references.

### Phase 5: Import, Backup UX, And Planning Mirror

Complete these issues near the end:

1. `0030` Add markdown tracker import planning.
2. `0032` Add backup and restore UX around existing JSON import/export.
3. `0012` Mirror existing sprint and issue planning docs into dogfood backlog.
4. `0010` Document the web UI modernization design decisions.

Expected implementation shape:

- Planning/import work should be documented and safe by default unless the issue explicitly requires executable import.
- Backup/restore UX wraps or documents existing JSON import/export without exposing secrets.
- Generated exports, backups, and tracker dumps remain ignored and uncommitted.
- Modernization decisions are documented and linked from README or Sprint 0043.

### Phase 6: Board And Drag-And-Drop Last

Complete these last because they depend on stable views, ordering, and status update behavior:

1. `0021` Add board-style workflow view.
2. `0036` Add drag-and-drop backlog priority ordering.
3. `0038` Add category recommendation assistant for issue creation.

Expected implementation shape:

- Board view can be server-rendered with form actions if that satisfies the issue. Do not introduce a frontend framework unless unavoidable.
- Drag-and-drop can be deferred only if the issue is explicitly closed as a non-MVP caveat by the user; otherwise implement it with minimal JavaScript and route tests for the underlying ordering endpoint.
- Category recommendations must remain project-scoped and explainable. Do not call external services.

## Remaining Tracker Issues

Finish all of these before closing Sprint 0043:

| Issue | Title |
|---|---|
| `0008` | Add browser-level manual UAT evidence for the modernized UI |
| `0019` | Add saved issue views for backlog, active sprint, blocked, done, and uncategorized work |
| `0024` | Add blocked indicator and dependency health summary |
| `0027` | Add global project search |
| `0028` | Add sprint and project progress summaries |
| `0033` | Add sprint and backlog navigation views |
| `0034` | Add issue edit sidebar for single-window editing |
| `0035` | Add inline status and priority dropdowns on issue lists |
| `0037` | Add category governance and recommended base taxonomy |
| `0039` | Add story grouping for complex features |
| `0040` | Add delivery phase field for issue lifecycle planning |
| `0042` | Add story and sprint rollup summaries |
| `0010` | Document the web UI modernization design decisions |
| `0020` | Add sortable backlog priority controls |
| `0021` | Add board-style workflow view |
| `0022` | Add roadmap or milestone grouping |
| `0023` | Add quick issue create and inline edit affordances |
| `0025` | Add issue comments or notes timeline |
| `0026` | Add labels and lightweight custom fields |
| `0029` | Add activity feed and recent changes view |
| `0030` | Add markdown tracker import planning |
| `0031` | Add GitHub reference fields without full sync |
| `0032` | Add backup and restore UX around existing JSON import/export |
| `0036` | Add drag-and-drop backlog priority ordering |
| `0038` | Add category recommendation assistant for issue creation |
| `0041` | Add story templates for common delivery patterns |
| `0012` | Mirror existing sprint and issue planning docs into dogfood backlog |

## Acceptance Criteria

Browser UAT:

- [ ] A dated UAT note exists under `documentation/uat/`.
- [ ] Desktop and mobile viewport notes are recorded.
- [ ] Setup/login, project, category, issue validation, dependency, sprint, assignment, close, and issue-log workflows are covered.
- [ ] Any failed browser step maps to a tracker issue or explicit non-MVP backlog note.

All product issues:

- [ ] Every remaining Sprint 0043 issue listed above is implemented, explicitly deferred with user-accepted caveat, or blocked by a named external action.
- [ ] Each completed issue has service/route/MCP/browser verification appropriate to its surface.
- [ ] Shared lifecycle and filtering behavior lives in service/repository helpers, not templates.
- [ ] Browser-facing behavior has browser or route-level evidence.
- [ ] MCP-facing parity is maintained when web features overlap MCP behavior.
- [ ] Schema changes, if any, include Alembic migration and empty-database upgrade evidence.

Tracker and docs:

- [ ] Completed tracker issues are closed with originating LLM, closed-by, close note, and evidence.
- [ ] Sprint 0043 markdown handoff is updated with commands, results, remaining open work, and STOP.
- [ ] No generated exports, backups, logs, database files, or credentials are committed.

## Verification Commands

Run the smallest relevant gate during implementation, then run the final gate before closeout:

```bash
docker compose -f deployment/docker-compose.local.yml config
docker compose -f deployment/docker-compose.local.yml build
docker compose -f deployment/docker-compose.local.yml run --rm app alembic upgrade head
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/
docker compose -f deployment/docker-compose.local.yml run --rm app python -m issue_tracker.mcp.server --smoke
docker compose -f deployment/docker-compose.local.yml up -d
curl -fsS http://localhost:8000/health
docker compose -f deployment/docker-compose.local.yml run --rm app python -m ruff check --no-cache .
git diff --check
LC_ALL=C grep -RIn '[^ -~]' README.md AGENTS.md .cursor/rules .github/workflows documentation src tests migrations deployment .env.example pyproject.toml alembic.ini
git status --short --branch --ignored
```

If import/export behavior is touched, also run:

```bash
docker compose -f deployment/docker-compose.local.yml run --rm app issue-tracker export-json 1 exports/manual-uat-project.json
docker compose -f deployment/docker-compose.local.yml run --rm app issue-tracker import-json exports/manual-uat-project.json Manual-UAT-Restored-Next --category-map IT-1=IT-1
```

## Allowed Side Effects

- Edit code, tests, and documentation in this repository.
- Update the local tracker database for Sprint 0043 issue status and evidence.
- Create ignored local generated files under `exports/` only for import/export smoke.
- Keep the local Docker Compose stack running if needed for browser verification.

## Disallowed Side Effects

- Do not commit secrets, `.env`, logs, database dumps, backups, generated exports, or local credentials.
- Do not run destructive reset commands unless the user explicitly confirms.
- Do not edit mirrored guidance in `spacemanspiff99/vibecoding`.
- Do not expand this prompt into production deployment, GitHub sync, multi-user auth, full markdown migration, or drag/drop planning unless all smaller Sprint 0043 slices are already complete and verified.

## Closing Sprint 0043

When all issues are complete:

1. Run the final verification gate.
2. Update local tracker issue statuses to `done` with originating LLM, closed-by, close note, and verification evidence.
3. Close Sprint 0043 in the local tracker.
4. Update `documentation/sprints/0043-overnight-modern-web-app-buildout.md` with final evidence and status `closed`.
5. Record final UAT notes under `documentation/uat/`.

## STOP

Stop only after one of these outcomes is recorded in both the tracker and `documentation/sprints/0043-overnight-modern-web-app-buildout.md`:

- Sprint 0043 complete: all assigned issues closed with evidence, final gates pass, and browser UAT is recorded.
- Sprint 0043 blocked: name exact blocker, command output summary, owner action, and the next smallest retry step.

The final response must include changed files, verification commands and results, blocked checks, tracker updates, and the remaining STOP handoff.
