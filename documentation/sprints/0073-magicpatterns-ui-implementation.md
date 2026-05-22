# Sprint 0073: MagicPatterns UI Implementation

Status: complete in the local tracker

Tracker sprint: `0073` Implement MagicPatterns-generated tracker UI

MagicPatterns source artifact: `documentation/design/magicpatterns/UI.tsx`

## Goal

Implement the MagicPatterns-generated Issue Tracker UI against the existing FastAPI + Jinja application without losing service-layer behavior, MCP parity, or tracker state integrity.

The MagicPatterns export is protected source design. Preserve its layout, spacing, visual hierarchy, labels, and component structure unless a targeted divergence is required for the server-rendered app. Any divergence must be documented here or in the closing UAT note.

## Model And Reasoning

Recommended model/reasoning: GPT-5.5 `medium` for normal template, static asset, route-test, and documentation work.

Escalate to GPT-5.5 `high` if the work unexpectedly touches schema/migrations, auth/secrets, deployment, MCP contracts, or data integrity.

Current session mismatch note: this sprint was created in the active Codex session using the available model. Future implementation prompts should explicitly request the recommended model/reasoning above before starting.

## Scope

- Use `documentation/design/magicpatterns/UI.tsx` as the source inventory for AppShell, Overview, Board, Backlog, Releases, Intake, IssueDetail, and IssueDrawer.
- Keep the application server-rendered unless a separate architecture decision explicitly approves adding a React runtime or frontend build step.
- Implement shared styling under the existing web surface, preferably with static CSS and progressive enhancement.
- Continue routing mutations through `IssueService`, `SprintService`, `CategoryService`, and existing repository invariants.
- Keep project-scoped data, category binding, issue lifecycle, dependency handling, close metadata, and MCP behavior intact.

## Implementation Map

| MagicPatterns Source | Server-rendered Implementation |
|---|---|
| `AppShell` | `src/issue_tracker/web/templates/base.html` gradient sidebar, top bar, search affordance, local indicator, and project-scoped navigation. |
| `Overview` | `src/issue_tracker/web/templates/project_detail.html` with live KPIs, workflow summary, saved views, quick create, release readiness, sprint progress, categories, and activity. |
| `Backlog` | `src/issue_tracker/web/templates/backlog.html` with search, saved views, draggable order form, inline priority update, category chips, and dependency indicators. |
| `Board` | `src/issue_tracker/web/templates/board.html` with sprint filtering, status columns, draggable visible order, card metadata, and service-backed status transitions. |
| `Releases` | `src/issue_tracker/web/templates/releases.html` with milestone progress cards, blocker and unscheduled counts, linked sprint badges, and readiness notes. |
| `Intake` | `src/issue_tracker/web/templates/intake.html` with title/priority controls, browser recording/upload UI, clarification flag, and intake queue. |
| `IssueDetail` / `IssueDrawer` | `src/issue_tracker/web/templates/issue_detail.html` with header metadata, summary/approach blocks, acceptance criteria, closeout record, activity, comments, references, and a persistent sidebar as the server-rendered drawer equivalent. |
| Categories / Sprints placeholders | `src/issue_tracker/web/templates/categories.html` and `src/issue_tracker/web/templates/sprints.html` project-scoped pages. |

Targeted divergence: the React runtime, Tailwind build, Framer Motion animation, and slide-out drawer were not added. The UI remains FastAPI/Jinja and uses inline CSS to preserve the MagicPatterns component intent without introducing an unapproved frontend build step.

## Out Of Scope

- Replacing the FastAPI/Jinja app with a React SPA.
- Adding a frontend build pipeline without explicit approval.
- Schema changes unless implementation evidence proves they are necessary.
- Reworking MagicPatterns visual design beyond targeted adaptation for the current app.
- Production deployment changes.

## Backlog

| Tracker ID | Issue | Category | Phase | Acceptance Summary |
|---|---|---|---|---|
| `0066` | Catalog MagicPatterns UI source and implementation map | `WEB-1` | UI foundation | Preserve and link the source artifact; map generated screens/components to current Jinja routes/templates; document any divergence. |
| `0067` | Adapt MagicPatterns visual system to server-rendered assets | `WEB-1` | Visual system | Reproduce typography, spacing, states, badges, cards, and navigation styling without adding an unapproved frontend build step. |
| `0068` | Implement MagicPatterns app shell and project workspace navigation | `WEB-2` | Navigation shell | Expose Overview, Board, Backlog, Releases, Intake, Categories, Sprints, Planning, and Backup navigation with project-scoped routes. |
| `0069` | Implement MagicPatterns backlog and board workflows | `WEB-2` | Backlog and board | Preserve filters, ordering, sprint scope, dependencies, status transitions, and card metadata on backlog and board screens. |
| `0070` | Implement MagicPatterns issue detail and drawer experience | `WEB-2` | Issue detail | Expose issue metadata, acceptance criteria, dependencies, comments, linked references, close metadata, and validation errors through existing services. |
| `0071` | Implement MagicPatterns releases, intake, and overview surfaces | `WEB-2` | Planning surfaces | Use live service data for overview, release rollups, and intake while preserving empty states and blocked/readiness indicators. |
| `0072` | Run MagicPatterns UI regression and UAT gate | `WEB-4` | Verification | Run containerized pytest and ruff gates; complete browser or route-level desktop/mobile checks; record dated UAT evidence. |

## Dependency-Aware Execution Plan

1. Complete `0066` first. Inventory the generated export, decide the target route/template/static file mapping, and record any necessary divergence before editing UI code.
2. Complete `0067` next. Establish the reusable visual system so later template work does not duplicate styling.
3. Complete `0068` before page-level rewrites. Navigation and layout should frame all later surfaces.
4. Complete `0069`, `0070`, and `0071` in that order unless implementation evidence shows a better sequence. Keep behavior wired through existing services.
5. Complete `0072` last with command evidence and browser or route-level UAT notes.

Subagents: none are authorized by this sprint creation request. If the user later explicitly authorizes parallel agents, split only across disjoint write scopes such as static CSS, backlog/board templates, issue detail templates, and UAT verification.

## Verification Commands

```bash
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/
docker compose -f deployment/docker-compose.local.yml run --rm app python -m ruff check --no-cache .
```

UI-facing changes also require browser or route-level verification that covers setup/login, project detail, overview, backlog, board, releases, intake, issue detail or drawer behavior, and sprint detail.

## Close Evidence

Route-level UAT note: `documentation/uat/2026-05-15-sprint-0073-route-uat.md`

Commands run on 2026-05-15:

```bash
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/integration/test_web_routes.py
docker compose -f deployment/docker-compose.local.yml run --rm app python -m ruff check --no-cache .
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/
```

Results:

- Web route tests: 10 passed.
- Ruff: all checks passed.
- Full tests: 26 passed, 1 skipped. The skipped test is the opt-in browser UAT guarded by `RUN_BROWSER_UAT=1`.
- Known warning: pytest could not write `.pytest_cache` inside the Docker-mounted app directory; this did not affect verification.

## STOP

Sprint `0073` is complete and closed with verification evidence.
