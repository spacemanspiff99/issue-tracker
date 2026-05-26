# Sprint Plan: AI Coding Workflow UX Reset Implementation

Status: draft sprint plan, backlog created, implementation not started

Created: 2026-05-25

Source six-pager: `documentation/planning/AI_CODING_WORKFLOW_UX_SIX_PAGER.md`

Tracker backlog created: `0154` through `0167`

Follow-on overnight execution sprint: `documentation/sprints/0168-overnight-dev-uat-comprehensive-validation.md`

Recommended model/reasoning: GPT-5.5 `high`

Use high reasoning because the plan touches workflow state, schema/backfill decisions, route and MCP contracts, MagicPatterns-protected UI surfaces, data cleanup, and manual UAT readiness.

## Goal

Implement the approved AI Coding Workflow UX six-pager until Issue Tracker is ready for local manual UAT of the full intake-to-closeout workflow.

This is not a cosmetic redesign. The work should make the app operate as a local-first AI coding workflow system: rough input becomes processable work, processable work becomes ready-for-Codex backlog, ready work moves into small sprints, Sprint Board execution preserves context, and closeout records verification evidence.

## Current Backlog Review

Active tracker project: `issue-tracker`

Current tracker state observed during planning:

- Total issues: 142 before creating this backlog.
- Active sprint: `0140` Urgent usability rescue: user-flow-first tracker cleanup.
- Sprint `0140` overlaps the six-pager and must be reconciled before new implementation starts.
- Open voice/audio/intake check found one relevant open issue: `0141` Fix browser audio recording controls that appear inert, currently `in-progress` / `implementing`.
- Historical voice/audio/intake matches are mostly `done`; they should not be re-opened unless the reconciliation issue finds missing evidence.
- Existing tracker issue `0153` is `test1`, `backlog`, `ready-for-codex`. Treat it as an accidental/test backlog item during cleanup planning; do not silently delete it.

Sprint `0140` status snapshot:

| ID | Title | Status | Workflow |
|---|---|---|---|
| `0141` | Fix browser audio recording controls that appear inert | in-progress | implementing |
| `0142` | Create user-flow-first UX map for human and AI tracker work | done | closed |
| `0143` | Add consistent info tooltip descriptions beside labels and controls | in-progress | implementing |
| `0144` | Clean up overview dashboard and make every component drill down | in-progress | implementing |
| `0145` | Repair backlog saved views and add Issues Not In Sprint view | in-progress | implementing |
| `0146` | Normalize status model with cancelled or won't do lifecycle | done | closed |
| `0147` | Alphabetize and numerically sort menus, dropdowns, and option lists | in-progress | implementing |
| `0148` | Redesign board sprint navigation for active, future, and historical sprints | in-progress | implementing |
| `0149` | Redesign releases page organization and navigation | in-progress | implementing |
| `0150` | Simplify project categories to a small useful taxonomy | done | closed |
| `0151` | Redesign sprints page default views and history navigation | in-progress | implementing |
| `0152` | Add end-to-end usability regression coverage for primary tracker flows | in-progress | implementing |

Decision: use `0154` as the reconciliation gate before executing the new backlog. It should decide which Sprint `0140` work is kept, closed with evidence, superseded, or carried forward.

## Created Implementation Backlog

The following tracker issues were created as backlog issues and marked `Ready for Codex`. They are not assigned to a sprint yet.

| Order | Tracker ID | Priority | Category | Issue |
|---:|---|---|---|---|
| 1 | `0154` | urgent | `PROD-1` | Reconcile AI workflow six-pager with Sprint 0140 and current checkout |
| 2 | `0155` | urgent | `IT-3` | Decide workflow state persistence and migration/backfill design |
| 3 | `0156` | high | `IT-4` | Define web and MCP contracts for AI workflow views |
| 4 | `0157` | urgent | `WEB-2` | Implement lifecycle status versus AI workflow state separation |
| 5 | `0158` | urgent | `WEB-3` | Make intake capture trustworthy and create Needs processing work |
| 6 | `0159` | high | `PROD-2` | Add processing path from raw intake to Ready for Codex |
| 7 | `0160` | urgent | `PROD-1` | Build backlog saved workflow views and exact filtered URLs |
| 8 | `0161` | urgent | `PROD-3` | Replace Lifecycle Dashboard with workflow command center |
| 9 | `0162` | high | `WEB-2` | Rename Board to Sprint Board and keep route-backed movement in context |
| 10 | `0163` | high | `WEB-2` | Reorder primary navigation and clarify page responsibilities |
| 11 | `0164` | high | `IT-1` | Implement accidental draft discard and durable cancel/archive policy |
| 12 | `0165` | high | `IT-2` | Plan and execute category consolidation and workflow backfill |
| 13 | `0166` | high | `WEB-3` | Add perceived-wait feedback for navigation and form submits |
| 14 | `0167` | urgent | `WEB-4` | Run full manual UAT readiness gate for AI workflow redesign |

## Dependency-Aware Sprint Plan

Do not create or start the tracker sprint records until `0154` finishes reconciliation. The plan below is the target sequence from investigation through manual UAT readiness.

### Sprint A: Reconciliation And Contract Decisions

Purpose: avoid duplicating or corrupting the active Sprint `0140` work and make the state/contract decisions before implementation.

Issues:

- `0154`: Reconcile six-pager with Sprint `0140` and current checkout.
- `0155`: Decide workflow state persistence and migration/backfill design.
- `0156`: Define web and MCP contracts for AI workflow views.

Key output:

- A current-state baseline that says which `0140` issues are closed, superseded, carried forward, or still required.
- A workflow persistence decision.
- Exact service, route, saved-view, and MCP contracts.

Verification:

```bash
python3 -m compileall src/issue_tracker
python3 -m pytest tests/unit/test_services.py tests/integration/test_mcp_tools.py tests/integration/test_web_routes.py -k "workflow or backlog or mcp"
```

STOP: Do not start UI implementation until this sprint names the workflow persistence model and the exact filtered URL/MCP contracts.

### Sprint B: Workflow Model And Intake Processing

Purpose: make rough input and processed work visibly different.

Issues:

- `0157`: Implement lifecycle status versus AI workflow state separation.
- `0158`: Make intake capture trustworthy and create Needs processing work.
- `0159`: Add processing path from raw intake to Ready for Codex.
- Carry forward `0141` if it is not closed with browser evidence during reconciliation.

Key output:

- Issue detail and lists show lifecycle status separately from AI workflow state.
- Voice/upload/manual rough input creates `Needs processing` work.
- Codex/human processing can move work to `Needs clarification` or `Ready for Codex`.

Verification:

```bash
python3 -m pytest tests/unit/test_services.py -k "workflow or voice or intake"
python3 -m pytest tests/integration/test_web_routes.py -k "workflow or intake"
RUN_BROWSER_UAT=1 python3 -m pytest tests/e2e/test_browser_uat.py -k intake
```

STOP: Do not call intake fixed until browser evidence shows recording or a clear actionable failure state.

### Sprint C: Backlog, Overview, And Navigation Reset

Purpose: turn the main surfaces into an actionable command center and workflow queues.

Issues:

- `0160`: Build backlog saved workflow views and exact filtered URLs.
- `0161`: Replace Lifecycle Dashboard with workflow command center.
- `0163`: Reorder primary navigation and clarify page responsibilities.
- `0166`: Add perceived-wait feedback for navigation and form submits.

Key output:

- Backlog owns workflow saved views.
- Overview owns actionable rollups and exact drill-downs.
- Navigation follows workflow order: Overview, Intake, Backlog, Sprint Board, Sprints, Releases, Categories.
- Navigation and form submits no longer feel frozen.

Verification:

```bash
python3 -m pytest tests/unit/test_services.py -k "backlog or workflow"
python3 -m pytest tests/integration/test_web_routes.py -k "project or backlog or overview"
RUN_BROWSER_UAT=1 python3 -m pytest tests/e2e/test_browser_uat.py
```

STOP: Do not close while any default Overview count lacks an exact filtered destination.

### Sprint D: Sprint Board, Durable Work Controls, And Cleanup Prep

Purpose: make execution reliable before data cleanup.

Issues:

- `0162`: Rename Board to Sprint Board and keep route-backed movement in context.
- `0164`: Implement accidental draft discard and durable cancel/archive policy.
- `0165`: Plan category consolidation and workflow backfill, but do not run data mutation until the plan is reviewed.

Key output:

- Board is Sprint Board.
- Route-backed movement stays on the selected board context.
- Accidental draft discard is separate from durable cancel/archive.
- Data cleanup has a reversible mapping and pre-mutation evidence.

Verification:

```bash
python3 -m pytest tests/unit/test_services.py -k "status or cancel or sprint"
python3 -m pytest tests/integration/test_web_routes.py -k "board or sprint or cancel or categor"
RUN_BROWSER_UAT=1 python3 -m pytest tests/e2e/test_browser_uat.py
```

STOP: Do not execute category or workflow backfill until pre-cleanup evidence and reversible mapping are written.

### Sprint E: Data Cleanup And Count Sanity

Purpose: align existing tracker data with the new workflow without losing history.

Issues:

- Finish `0165`.
- Include any carry-forward cleanup tasks found by `0154`.

Key output:

- Categories are consolidated or mapped according to the approved taxonomy.
- `IT-1` through `IT-6` prevention categories remain available for standards-sensitive work.
- Raw intake and rough items are backfilled to `Needs processing` where appropriate.
- Stale sprint history is hidden from defaults without deleting history.
- Dashboard/command-center counts match exact filtered destinations.

Verification:

```bash
python3 -m pytest tests/unit/test_services.py tests/integration/test_web_routes.py -k "categor or workflow or sprint or backlog"
python3 -m compileall src/issue_tracker
```

STOP: Do not treat cleanup complete without before/after evidence and sample record checks.

### Sprint F: Manual UAT Readiness Gate

Purpose: prove the six-pager implementation is ready for manual UAT.

Issues:

- `0167`: Run full manual UAT readiness gate for AI workflow redesign.

Required gate:

```bash
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml config
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml build
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml run --rm app alembic upgrade head
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml up -d app
curl -fsS http://localhost:18000/health
RUN_BROWSER_UAT=1 python3 -m pytest tests/e2e/test_browser_uat.py
```

Manual UAT must cover:

- Setup/login.
- Intake recording success or visible actionable failure.
- Audio upload fallback.
- Manual quick intake to `Needs processing`.
- Processing into `Needs clarification` and `Ready for Codex`.
- Backlog workflow saved views.
- Overview command-center count drill-downs.
- Sprint Board route-backed movement.
- Accidental draft discard.
- Durable cancel/archive.
- Closeout evidence.
- Desktop and mobile page usability.

STOP: The app is not manual-UAT-ready until all automated gates pass or blockers are recorded with exact retry commands, and written UAT notes exist under `documentation/uat/`.

## Parallelism Guidance

Use sequential work for:

- `0154`, `0155`, and `0156`; these define the state and contract baseline.
- Any schema migration and data backfill work.
- Final manual UAT readiness.

Subagents may run in parallel only after Sprint A is complete and only with disjoint write scopes:

- Service/schema/MCP contract worker: `0155`, `0156`, service tests, MCP tests.
- Intake/detail worker: `0157`, `0158`, `0159`, issue detail, intake routes/templates, browser intake tests.
- Backlog/overview/navigation worker: `0160`, `0161`, `0163`, `0166`, route/browser tests.
- Sprint Board/work controls worker: `0162`, `0164`, board/sprint/cancel tests.

Merge sequentially through service-layer tests before broad browser UAT.

## Manual UAT Readiness Definition

The app is ready for manual UAT when:

- All issues `0154` through `0167` are done or explicitly deferred by the user.
- Sprint `0140` is closed or its remaining items are explicitly superseded/deferred with evidence.
- Local preflight build, migration, full pytest, health, MCP, and browser gates pass.
- A written UAT note records pass/fail evidence and exact remaining risks.
- No destructive data refresh, UAT deploy, production deploy, or remote mutation is implied by this plan.

## Execution Evidence

- 2026-05-26: Follow-on overnight sprint `0168` was created to finish dev readiness, source-control closeout, UAT deploy, and comprehensive UAT.
- 2026-05-26: Local dev preflight passed in the `0168` sprint. Evidence is recorded in `documentation/uat/2026-05-26-sprint-0168-dev-preflight.md`.

## STOP

Stop here until the user chooses whether to start Sprint A. Do not implement the six-pager, create/start tracker sprint records, run data cleanup, deploy, or mutate remote environments from this plan alone.
