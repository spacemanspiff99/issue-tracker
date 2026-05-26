# Sprint 0140: Urgent Usability Rescue

Status: active

Created: 2026-05-24

Tracker sprint: `0140` Urgent usability rescue: user-flow-first tracker cleanup

Source context:

- User feedback: record audio buttons appear inert; overview, backlog saved views, board sprint navigation, releases, categories, and sprints pages are hard to use; controls need discoverable descriptions; filters and menus need predictable behavior.
- UX principles: `documentation/guides/ai-coding-tracker-ux.md`
- Sprint UX flow map: `documentation/guides/issue-tracker-ux-flow-map.md`
- Product guide: `documentation/guides/product-guide.md`
- Protected UI source: `documentation/design/magicpatterns/UI.tsx`
- Previous related sprints: `documentation/sprints/0050-backlog-ux-release-voice-feedback-playwright.md`, `documentation/sprints/0078-sprint-0073-ui-regression-fixes.md`, and `documentation/sprints/0129-uat-as-staging-dev-seed-production-readiness.md`

## Goal

Rescue the core tracker usability by starting from actual user and AI-agent flows, then fixing the broken intake path, misleading dashboard and saved-view navigation, overgrown sprint/release/category surfaces, inconsistent sorting, and missing contextual help.

This sprint should not become a cosmetic restyle. It should make the tracker easier to operate when a human is capturing messy feedback and when Codex or another AI agent needs deterministic URLs, clear state, and recoverable context.

## Model And Reasoning

Recommended model/reasoning: GPT-5.5 `high`.

Use high reasoning because the work touches schema/status lifecycle, service filters, MCP parity, many Jinja surfaces, browser audio behavior, MagicPatterns-protected UI, route contracts, and dogfood tracker state.

Planning note: this sprint was created in the available Codex session. Implementation sessions should request GPT-5.5 `high`; if unavailable, record the model mismatch before changing code.

Execution note, 2026-05-24: this implementation is running in a GPT-5 Codex session, not the requested GPT-5.5 `high` session. The mismatch is accepted for the current local execution because the user explicitly asked to execute the sprint in this session; schema, MCP, and browser-facing changes still require the verification gates below before closeout.

## Intake Check

Before creating this backlog, the active tracker project was queried for open items matching `To process`, `voice-feedback`, `audio`, `intake`, or `clarify`.

- Active project: `issue-tracker`.
- Open matching voice/audio/intake issues: none.
- Decision: the newly reported inert record-audio button is captured as urgent issue `0141`; no prior open intake issue is deferred.

## User Flow Baseline

Implementation starts by documenting and validating these flows, then uses them to judge each page change:

1. Capture rough input: user records audio or writes a note, gets immediate feedback, and creates a discoverable intake/backlog item.
2. Triage backlog: user or AI opens backlog saved views, finds unsprinted/unblocked/urgent work, and gets shareable filtered URLs.
3. Plan sprint: user sees active and not-started work first, adds issues to a sprint, and can still find old sprints without drowning in history.
4. Execute board work: user switches between active/future sprints and archived sprints without a giant flat selector.
5. Navigate progress: overview and releases expose counts that are all clickable drill-downs into filtered issue lists.
6. Close or cancel work: status, close metadata, and filters distinguish `done` from `cancelled/won't do`.
7. Recover context for AI: every relevant page gives descriptions, deterministic links, and enough labels/state for an agent to continue safely.

## Backlog

| Order | Tracker ID | Phase | Priority | Issue |
|---:|---|---|---|---|
| 1 | `0141` | P0 intake unblocker | urgent | Fix browser audio recording controls that appear inert |
| 2 | `0142` | P0 design spine | urgent | Create user-flow-first UX map for human and AI tracker work |
| 3 | `0143` | P1 global affordances | high | Add consistent info tooltip descriptions beside labels and controls |
| 4 | `0144` | P1 overview | urgent | Clean up overview dashboard and make every component drill down |
| 5 | `0145` | P1 backlog | urgent | Repair backlog saved views and add Issues Not In Sprint view |
| 6 | `0146` | P2 lifecycle | high | Normalize status model with cancelled or won't do lifecycle |
| 7 | `0147` | P2 navigation hygiene | high | Alphabetize and numerically sort menus, dropdowns, and option lists |
| 8 | `0148` | P2 board | high | Redesign board sprint navigation for active, future, and historical sprints |
| 9 | `0149` | P2 releases | high | Redesign releases page organization and navigation |
| 10 | `0150` | P2 taxonomy | high | Simplify project categories to a small useful taxonomy |
| 11 | `0151` | P2 sprints | high | Redesign sprints page default views and history navigation |
| 12 | `0152` | P3 verification | high | Add end-to-end usability regression coverage for primary tracker flows |

## Phase Plan

### P0: Stop Losing Input

Do first and keep tightly scoped.

- `0142` writes the user-flow map and page responsibility baseline.
- `0141` debugs record-audio from real browser evidence and fixes the inert button path.

These can proceed in parallel only if write scopes stay separate: `0142` writes documentation/planning, while `0141` writes intake template/route/tests.

### P1: Make Navigation Deterministic

Do next because these are the highest-frequency navigation failures.

- `0143` creates the reusable info affordance and applies it to the core surfaces.
- `0144` makes overview readable and turns every card/count into a filtered drill-down.
- `0145` fixes backlog saved views and adds `Issues Not In Sprint`.

Implement service/filter behavior before template polish so route and MCP parity can be tested.

### P2: Reduce Organizational Noise

Do after the filtering spine works.

- `0146` adds the cancelled/won't-do lifecycle with migration and service/web/MCP parity.
- `0147` audits and fixes menu/dropdown ordering.
- `0148` separates board sprint navigation into active/future/history.
- `0149` reorganizes release navigation around current/upcoming/archive and clickable rollups.
- `0150` consolidates category taxonomy safely.
- `0151` makes sprints default to actionable work and moves closed history out of the default path.

Subagents may be used only with disjoint write scopes: one for status/schema/MCP, one for board/sprints, one for releases/categories, and one for route/browser tests. Merge sequentially through the service layer.

### P3: Prove The Flows

`0152` extends browser regression coverage around the actual flows: intake recording, overview drill-downs, backlog saved views, board sprint navigation, releases, categories, sprints defaults, tooltips, desktop, and mobile.

## Acceptance Criteria

### `0141` Fix Browser Audio Recording Controls That Appear Inert

Pass:

- Clicking record gives immediate visible feedback: requesting microphone, recording, permission denied, unsupported browser, or secure-context required.
- Stop attaches a non-empty audio file and shows playback/attachment state before submit.
- Audio-only urgent intake creates a discoverable urgent voice-feedback issue without requiring title text.
- Upload fallback remains usable when recording is unavailable.
- Browser coverage exercises fake microphone recording and a user-visible failure state.

Verification:

```bash
RUN_BROWSER_UAT=1 python -m pytest tests/e2e/test_browser_uat.py -k intake
```

STOP: Do not mark complete until a real browser interaction proves the record button changes state or displays the exact actionable error.

### `0142` Create User-Flow-First UX Map For Human And AI Tracker Work

Pass:

- A durable UX flow note names the primary human and AI-agent flows across overview, backlog, board, sprints, releases, categories, intake, and issue detail.
- Each page has a clear primary job, primary actions, drill-down targets, and empty-state behavior.
- The note identifies which dashboard cards, saved views, menus, and filters need query-string URLs for shareable AI/human handoff.
- The remaining sprint issues link back to this flow model before implementation.

Verification:

```bash
python -m compileall src/issue_tracker
```

STOP: Do not start broad page redesign work until the flow model is written and linked from the sprint plan.

### `0143` Add Consistent Info Tooltip Descriptions Beside Labels And Controls

Pass:

- A reusable info component supports mouse hover and keyboard focus with accessible text.
- Overview, backlog, board, sprints, releases, categories, intake, planning, backup, guidance sync, project detail, and issue detail use the component for non-obvious labels and controls.
- Descriptions explain what the control does, what data it changes, and where applicable what filter URL it applies.
- Tooltip content does not overlap critical UI on desktop or mobile.

Verification:

```bash
python -m pytest tests/integration/test_web_routes.py
RUN_BROWSER_UAT=1 python -m pytest tests/e2e/test_browser_uat.py
```

STOP: Do not ship partial page coverage without recording exactly which pages still lack info affordances.

### `0144` Clean Up Overview Dashboard And Make Every Component Drill Down

Pass:

- Overview cards are organized into a small number of scannable groups with clear hierarchy and no overlapping content on desktop/mobile.
- Clicking Done opens issues filtered to done; backlog opens backlog issues; in-progress opens in-progress; blocked opens blocked; uncategorized opens uncategorized; active sprint opens the active sprint/board filter.
- Dashboard links preserve project context and use shareable URLs rather than hidden server-side state.
- Empty states explain the next action instead of showing noisy blank components.
- Route or browser tests prove each dashboard drill-down lands on the expected filtered page.

Verification:

```bash
python -m pytest tests/integration/test_web_routes.py -k "project or backlog or board"
RUN_BROWSER_UAT=1 python -m pytest tests/e2e/test_browser_uat.py
```

STOP: Do not close while any dashboard component is decorative only or links to an unfiltered destination.

### `0145` Repair Backlog Saved Views And Add Issues Not In Sprint View

Pass:

- All backlog saved views stay on the backlog page and apply the selected filter visibly.
- Issues Not In Sprint shows open issues with no current sprint membership and excludes closed/done historical work unless explicitly requested.
- Saved views include all, backlog, active sprint, blocked, done, uncategorized, and not in sprint.
- The selected saved view is visually active and reflected in the URL.
- Service and route tests cover each saved view.

Verification:

```bash
python -m pytest tests/unit/test_services.py tests/integration/test_web_routes.py -k backlog
```

STOP: Do not close until clicking each saved view from the rendered backlog page proves it remains on backlog and filters correctly.

### `0146` Normalize Status Model With Cancelled Or Won't Do Lifecycle

Prevention checklist:

- `IT-1`: Verify tracker state before and after status mutations.
- `IT-3`: Add and test the Alembic migration before relying on the new status.
- `IT-4`: Keep MCP issue search/list output compact and parity-backed.

Pass:

- Issue status options are backlog, in-progress, done, and cancelled/won't do with one canonical stored value and clear display label.
- Cancelled/won't do preserves immutable close/cancel metadata equivalent to done closeout metadata.
- Overview, backlog, board, issue detail, MCP search, import/export, and tests understand the new status.
- Alembic migration works on an empty database and preserves existing data.
- Filters and dashboard counts include cancelled/won't do where appropriate without mixing it into done.

Verification:

```bash
alembic upgrade head
python -m pytest tests/unit/test_services.py tests/integration/test_mcp_tools.py tests/integration/test_web_routes.py
```

STOP: Do not mutate the enum without a migration and parity tests for service, web, and MCP behavior.

### `0147` Alphabetize And Numerically Sort Menus, Dropdowns, And Option Lists

Pass:

- Project, category, sprint, release/milestone, status, saved-view, and board dropdown/list ordering rules are documented and implemented.
- Numeric IDs and sprint sequences sort naturally by sequence, not string order.
- Alphabetical lists use case-insensitive ordering.
- Tests or browser assertions cover representative dropdowns, including the board sprint selector.

Verification:

```bash
python -m pytest tests/integration/test_web_routes.py
RUN_BROWSER_UAT=1 python -m pytest tests/e2e/test_browser_uat.py
```

STOP: Do not close until the board dropdown and at least one category/release/sprint menu are verified from rendered HTML.

### `0148` Redesign Board Sprint Navigation For Active, Future, And Historical Sprints

Pass:

- Board defaults to active/current sprint work without flooding the user with old sprints.
- Future/planned sprints are visible as a small queue or segmented control when present.
- Closed sprints are in a searchable/collapsible history sorted newest first with clear done/closed metadata.
- Selecting any sprint updates the board URL and board contents deterministically.
- The UX scales to at least 100 closed sprints without making active work hard to find.

Verification:

```bash
python -m pytest tests/integration/test_web_routes.py -k board
RUN_BROWSER_UAT=1 python -m pytest tests/e2e/test_browser_uat.py
```

STOP: Do not close with a flat sprint dropdown that becomes unusable with many closed sprints.

### `0149` Redesign Releases Page Organization And Navigation

Pass:

- Releases are grouped into current/upcoming/archive or equivalent user-facing sections with predictable sorting.
- Each release row/card shows total, done, blocked, unscheduled, readiness notes, and linked sprints without visual clutter.
- Clicking release counts opens the correct filtered issue list.
- Empty/unplanned work is clearly separated from named releases.
- Desktop and mobile layouts are scannable and do not require reading every issue inline.

Verification:

```bash
python -m pytest tests/integration/test_web_routes.py -k releases
RUN_BROWSER_UAT=1 python -m pytest tests/e2e/test_browser_uat.py
```

STOP: Do not close until a user can find current release blockers and unplanned work in two clicks or fewer.

### `0150` Simplify Project Categories To A Small Useful Taxonomy

Prevention checklist:

- `IT-2`: Verify acceptance criteria are required, category checklists are preserved where needed, and project taxonomies remain project-scoped data.

Pass:

- The desired default taxonomy contains only a few categories and is documented with descriptions and checklists.
- Existing issue categories are mapped or archived without losing issue history.
- Category selectors become short, alphabetized, and understandable.
- Issue log prevention checklist behavior still works for IT-* standards when those standards are explicitly touched.
- Tests cover category list display and issue category assignment after consolidation.

Verification:

```bash
python -m pytest tests/unit/test_services.py tests/integration/test_web_routes.py -k categor
```

STOP: Do not delete or remap categories without a reversible mapping note and tests proving existing issues remain readable.

### `0151` Redesign Sprints Page Default Views And History Navigation

Pass:

- Sprints page defaults to active and not-started/planned sprints only.
- Closed sprints move into a separate history section with newest-first sorting, search, and pagination or collapse behavior.
- Sprint status terminology is consistent across service, page, board, and filters.
- The page shows next action, issue counts, blockers, and progress for visible sprints without overwhelming the user.
- Route/browser tests verify default visibility and history access.

Verification:

```bash
python -m pytest tests/integration/test_web_routes.py -k sprint
RUN_BROWSER_UAT=1 python -m pytest tests/e2e/test_browser_uat.py
```

STOP: Do not close while closed sprint history still dominates the default sprints page.

### `0152` Add End-To-End Usability Regression Coverage For Primary Tracker Flows

Pass:

- Browser coverage follows the primary user-flow map created in this sprint.
- Tests assert clicked dashboard/saved-view/release/board links apply expected filters, not merely that pages return 200.
- Desktop and mobile screenshots or assertions prove tooltips and dense navigation do not overlap critical UI.
- The suite can run against local dev without destructive database resets.
- Final sprint closeout records pass/fail evidence for every issue.

Verification:

```bash
RUN_BROWSER_UAT=1 python -m pytest tests/e2e/test_browser_uat.py
python -m pytest tests/
```

STOP: Sprint `0140` remains active until all usability issues pass verification or the user explicitly accepts named deferrals.

## STOP

Sprint `0140` is active. Do not close it until issues `0141` through `0152` are done with verification evidence, or the user explicitly accepts named deferrals.

## Implementation Evidence: 2026-05-24

Completed in the current local checkout:

- `0142`: flow model created at `documentation/guides/issue-tracker-ux-flow-map.md` and linked from this sprint plus README.
- `0143`: reusable `_components.html` info tooltip added and applied across overview, backlog, board, sprints, releases, categories, intake, planning, backup, Guidance Sync, sprint detail, and issue detail.
- `0144`: overview dashboard metrics now drill down to filtered backlog or board URLs.
- `0145`: backlog saved views stay on `/projects/{project_id}/backlog`, expose active state, and include `Issues Not In Sprint`.
- `0146`: cancelled/won't-do lifecycle added with Alembic migration `0004_cancelled_issue_status.py`, terminal metadata, service/web/MCP parity, and separate saved view.
- `0147`: category sorting, status lifecycle ordering, sprint history ordering, and release grouping rules implemented from the UX flow map.
- `0148`: board navigation separates active/planned sprint links, all-work mode, and collapsed closed history.
- `0149`: releases page groups current/upcoming/archive/unplanned work and links count rollups into filtered backlog URLs.
- `0150`: recommended project taxonomy reduced to `BUG`, `DOCS`, `FEATURE`, `OPS`, `UX`, plus retained `IT-1` through `IT-6` prevention categories; existing categories are preserved.
- `0151`: sprints page defaults to active/planned work and collapses searchable closed history.
- `0152`: route/service/MCP tests and Playwright script assertions were extended for the new primary flows.

Verification run:

```bash
docker compose -f deployment/docker-compose.local.yml run --rm app python -m compileall src/issue_tracker tests/e2e/test_browser_uat.py
docker compose -f deployment/docker-compose.local.yml run --rm app alembic upgrade head
docker compose -f deployment/docker-compose.local.yml exec postgres createdb -U issue_tracker issue_tracker_empty_0140
docker compose -f deployment/docker-compose.local.yml run --rm -e DATABASE_URL=postgresql+psycopg://issue_tracker:issue_tracker@postgres:5432/issue_tracker_empty_0140 app alembic upgrade head
docker compose -f deployment/docker-compose.local.yml exec postgres dropdb -U issue_tracker issue_tracker_empty_0140
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/unit/test_services.py tests/integration/test_mcp_tools.py tests/integration/test_web_routes.py -q
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/ -q
docker compose -f deployment/docker-compose.local.yml run --rm app python -m ruff check --no-cache .
```

Results:

- Compile: passed.
- Live dev database migration to `0004`: passed.
- Empty PostgreSQL database migration to head: passed, then the throwaway database was dropped.
- Focused unit/MCP/web route tests: `33 passed`.
- Full non-browser suite: `51 passed, 1 skipped`.
- Ruff: passed.
- Browser gate with `RUN_BROWSER_UAT=1`: blocked before app interaction because the container Playwright cache is missing Chromium at `/home/appuser/.cache/ms-playwright/chromium_headless_shell-1223/chrome-headless-shell-linux64/chrome-headless-shell`. Project rules prohibit Codex from installing missing tooling. Re-run after the owner installs Playwright browsers in the app image/cache.
- Tracker issues `0142`, `0146`, and `0150` were closed with verification notes. Issues `0141`, `0143`, `0144`, `0145`, `0147`, `0148`, `0149`, `0151`, and `0152` remain in progress with a tracker comment noting the blocked browser gate.

Current STOP:

Sprint `0140` remains active. Do not close issues `0141` and `0152`, or the sprint, until the Playwright browser gate runs successfully and proves the record button changes state or displays the exact actionable error in a real browser. The implementation is otherwise ready for that browser verification pass.
