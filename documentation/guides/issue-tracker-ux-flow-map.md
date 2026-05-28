# Issue Tracker UX Flow Map

Linked sprint: `documentation/sprints/0140-urgent-usability-rescue.md`

This map is the Sprint 0140 baseline for human and AI-agent tracker work. It keeps page changes tied to the actual jobs users need to complete instead of cosmetic reshuffling.

## Primary Flows

### Capture Rough Input

- Entry points: project overview, intake page, and issue detail links back to intake.
- Human job: record or upload messy feedback, optionally add notes, see immediate recording state, and create a backlog item without needing a polished title.
- AI-agent job: find fresh `voice-feedback`, `intake`, `clarify`, or `To process` work from stable filtered URLs and inspect the linked local artifact path.
- Required URLs: `/projects/{project_id}/intake` and backlog view links for intake-related labels or text search.
- Empty state: explain that no intake issues exist and offer the recording/upload form as the next action.

### Triage Backlog

- Entry points: overview cards, backlog saved views, issue detail next/previous navigation, and MCP `issue.search`.
- Human job: separate all work, unstarted backlog, blocked work, done work, uncategorized work, active sprint work, and work not assigned to any sprint.
- AI-agent job: receive deterministic URLs with visible query parameters so a handoff can reopen the same filtered set.
- Required URLs: `/projects/{project_id}/backlog?view=all`, `backlog`, `active-sprint`, `blocked`, `done`, `cancelled`, `uncategorized`, and `not-in-sprint`.
- Empty state: name the selected view and explain the next action, such as creating an issue, assigning a sprint, or clearing blockers.

### Plan Sprint

- Entry points: sprints page, backlog issue assignment controls, board sprint navigation, and sprint detail.
- Human job: see active and planned work first, add issues to a sprint, and find old sprints only when needed.
- AI-agent job: identify the active sprint, future planned sprints, and closed history without parsing a long flat selector.
- Required URLs: `/projects/{project_id}/sprints`, `/projects/{project_id}/sprints?history=1`, and `/projects/{project_id}/board?sprint_id={id}`.
- Empty state: show how to create the next sprint and where backlog candidates live.

### Execute Board Work

- Entry points: board tab and active sprint drill-downs.
- Human job: inspect current work by status and change scope between active, future, and historical sprints.
- AI-agent job: reopen a board URL with an explicit `sprint_id` and know whether that sprint is active, planned, or closed.
- Required URLs: `/projects/{project_id}/board`, `/projects/{project_id}/board?sprint_id={id}`, and backlog saved views for active sprint work.
- Empty state: explain whether the selected sprint has no issues or the project has no active sprint.

### Navigate Progress

- Entry points: overview dashboard and releases page.
- Human job: click counts directly into the filtered issue list behind that metric.
- AI-agent job: cite shareable links for total, backlog, in-progress, done, cancelled, blocked, uncategorized, active sprint, release blockers, and unscheduled work.
- Required URLs: overview cards must point to filtered backlog or board URLs; release counts must point to backlog URLs with `milestone` plus optional status/scope filters.
- Empty state: reduce noise and point to the next useful setup action.

### Close Or Cancel Work

- Entry points: issue detail status controls, closeout controls, backlog saved views, overview status cards, board columns, MCP status update.
- Human job: distinguish completed work from cancelled or won't-do work while preserving immutable close/cancel metadata.
- AI-agent job: search closed and cancelled records separately and avoid treating cancelled work as delivered.
- Required URLs: backlog saved views for `done` and `cancelled`; MCP `issue.search` status filters for both.
- Empty state: explain that cancelled items remain historical evidence but are excluded from delivery completion counts.

### Recover Context For AI

- Entry points: every project tab, issue detail, guidance sync, backup, planning, and MCP tools.
- Human job: leave enough labels, descriptions, and evidence for another session to continue safely.
- AI-agent job: understand what each page and control changes, what filters are active, and where durable notes live.
- Required URLs: all saved views and drill-downs use query strings; non-obvious labels have accessible info text.
- Empty state: describe the missing setup or evidence without hiding the command or route needed to produce it.

## Page Responsibilities

| Page | Primary job | Primary actions | Drill-down targets | Empty state |
|---|---|---|---|---|
| Overview | Summarize project state and route users to work | Open backlog views, board, intake, releases, categories | Filtered backlog, active board, intake queue, release blockers | Explain the next useful setup or triage action |
| Backlog | Search and sort issue lists through saved views | Select view, search, create issue, assign category/status | Issue detail, active sprint board, uncategorized and unsprinted sets | Name the active view and how to add matching work |
| Board | Execute sprint-scoped work | Switch active/planned/history sprint, open issues | Sprint detail, issue detail, backlog active-sprint view | Explain whether no sprint or no sprint issues exist |
| Sprints | Plan active and future iterations | Create sprint, open active/planned/history sections | Sprint detail and board sprint URLs | Prompt sprint creation or backlog triage |
| Releases | Understand milestone readiness | Open current/upcoming/archive releases and issue counts | Filtered backlog by milestone, blocker, unscheduled, status | Separate unplanned work and explain how to set milestones |
| Categories | Maintain project taxonomy | Create/update categories, assign issues elsewhere | Filtered backlog by category | Explain the default taxonomy and why categories are project-scoped |
| Intake | Capture raw feedback | Record, stop, upload, flag clarify, create intake issue | Intake issue detail and backlog intake search | State no current intake and show capture controls |
| Issue Detail | Preserve executable context | Update status/workflow/category/metadata, close, comment, assign sprint | Related dependencies, sprint, release, intake | Show missing AC, category, or metadata as next actions |
| Planning | Keep durable handoffs discoverable | Open docs, prompts, sprints, guidance | Sprint docs, prompts, project plan | Explain where to create durable plans |
| Backup | Preserve recoverable state | Export sanitized bundle, inspect artifact backup plan | Backup health and artifact checks | Explain missing tools or credentials as blocked owner actions |
| Guidance Sync | Keep external rule guidance aligned | Scan, review drift, create proposals | Drift detail and proposal references | Explain no sources, no scan, or no drift |
| Project Detail | Project command center | Open tabs, create quick issue/sprint, review activity | Same filtered project tabs | Guide first issue/category/sprint setup |

## Sorting Rules

- Status order is lifecycle order: backlog, in-progress, done, cancelled/won't do.
- Sprint and issue IDs sort numerically by project-local sequence, not lexicographically.
- Active and planned sprints sort newest first when scanning current work; closed history sorts newest first and stays outside the default view.
- Category, project, release, saved-view, and label lists sort case-insensitively by display name unless a lifecycle order is explicitly documented.
- `Unplanned` and `Uncategorized` are always grouped separately from named release/category values.

## Default Taxonomy

The small default project taxonomy for new or consolidated projects is:

- `BUG`: user-visible broken behavior or regression.
- `FEATURE`: new user-facing capability.
- `UX`: usability, navigation, copy, accessibility, and workflow clarity.
- `OPS`: deployment, runtime, backup, observability, and configuration.
- `DOCS`: durable guidance, prompts, planning, and evidence.
- `IT-1` through `IT-6`: retained only for issue-log prevention standards and schema/MCP/auth/deployment safety work.

Existing categories must not be deleted blindly. When consolidating, preserve readable history and record any reversible mapping in the sprint or issue closeout.
