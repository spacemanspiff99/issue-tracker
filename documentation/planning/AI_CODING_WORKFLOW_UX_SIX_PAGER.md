# AI Coding Workflow UX Six-Pager

Date: 2026-05-25

Status: Reviewed by user; implementation backlog and sprint planning authorized

Authoring context: Prepared from `documentation/prompts/0153-ai-coding-workflow-ux-six-pager.md`, Sprint 0140 usability evidence, the product guide, the AI coding tracker UX guide, the UX flow map, the manual UAT guide, and the protected MagicPatterns UI source. The user reviewed this six-pager on 2026-05-25 and authorized backlog/sprint planning. Implementation remains gated by the follow-up sprint plan.

Follow-up sprint plan: `documentation/sprints/0154-ai-coding-workflow-ux-reset-implementation-plan.md`

Model note: The recommended session for this product architecture work is GPT-5.5 with high reasoning. This draft was prepared in the available Codex GPT-5-class session, so the model/reasoning mismatch is recorded here for review before implementation planning proceeds.

## Executive Summary

Issue Tracker should stop presenting itself as a general issue database and become the operating system for AI coding work. Its core job is to capture rough human input, process that input into executable Codex work, preserve enough context for another session to continue safely, and prove that work was verified before it is closed.

The current product has the raw parts: intake, issues, workflow metadata, sprints, categories, releases, a board, and MCP access. The problem is that these parts do not yet form one obvious workflow. The user sees big counts, raw status/category noise, inert-feeling controls, unclear page purposes, and navigation that feels frozen when a request is slow. Codex sees related problems: many surfaces expose data without making the next action or exact filtered state deterministic.

The recommendation is a product and information architecture reset:

1. Make rough intake a first-class state, not a hidden variant of backlog.
2. Separate lifecycle status from AI workflow/readiness state.
3. Make each primary page responsible for one job in the end-to-end workflow.
4. Replace the Lifecycle Dashboard with an actionable command center and saved workflow views.
5. Rename Board to Sprint Board and constrain it to active sprint execution.
6. Consolidate categories to a small project taxonomy while preserving `IT-*` prevention categories for standards-sensitive work.
7. Treat all counts as promises: every count must link to the exact filtered list it summarizes.
8. Add low-cost perceived-wait feedback before expensive indexing or broad query optimization.
9. Preserve MagicPatterns layout and component structure unless a named workflow change requires a targeted adjustment.

The immediate next step is user review of this six-pager. If approved, the next artifact should be a set of user stories and issue prompts, followed by tracker issue creation and sprint planning.

## Future-State Narrative

Press release draft, written from the future:

Issue Tracker now gives local AI coding work a clear path from messy feedback to verified delivery. A user can open Intake, record a voice memo, upload an audio file, or type a rough note. The tracker immediately shows whether it is recording, waiting for microphone permission, uploading, saving, or blocked by a browser limitation. The raw item lands in `Needs processing`, where it is visible to both the web UI and Codex.

Codex can ask the tracker for the next raw item, read the note and artifact reference, and process it into a clear issue: summary, acceptance criteria, proposed approach, verification commands, model/reasoning recommendation, and STOP handoff. If the input is ambiguous, Codex moves it to `Needs clarification` and records exact questions. When it is executable, Codex marks it `Ready for Codex`.

The human owner no longer has to interpret a wall of statuses. Overview shows only actionable rollups and next actions. Backlog is where ready work is prioritized and cleaned. Sprint planning selects a small batch of ready work. Sprint Board shows only active execution and reliable route-backed movement controls. Issue detail remains the canonical record, including evidence and immutable close metadata. Cancelled work remains searchable history without being mixed into delivered work.

The product feels responsive because every navigation action acknowledges the click immediately. Heavy pages show busy states and use cheaper default queries. Counts drill into exact saved views, so neither the human owner nor Codex has to guess what a number means.

## Customer Problem And UAT Failure Analysis

The customer is not asking for more dashboard widgets. The customer is asking for a trustworthy workflow. The current UAT failures are symptoms of one product problem: the app exposes records before it explains what state the work is in, who should act next, and what page owns the next step.

| UAT finding | Product failure | Recommendation |
|---|---|---|
| Voice Intake then Record Audio appears to do nothing | Capture has no visible state machine for permission, recording, errors, and attachment readiness | Intake must show immediate recording/requesting/error/upload/attached states and create `Needs processing` work |
| Navigation feels frozen | Requests do not acknowledge click/wait states quickly enough | Add immediate active/busy feedback within 100 ms and visible loading for slow transitions |
| Lifecycle Dashboard count links land on safe or empty views | Counts are aggregates without exact filter contracts | Every count must link to a deterministic filtered backlog, sprint board, or issue list URL |
| Lifecycle Dashboard exposes too much status/category noise | Raw operational data is being treated as guidance | Replace or reframe it as workflow-focused command center rollups and saved views |
| Overview and active sprint show huge counts such as 140 issues | The UI shows scale without decision support | Default surfaces should show actionable queues and next actions, not all records |
| Too many categories | Taxonomy is doing workflow work and historical artifact work | Consolidate to 5 or 6 primary categories, preserving `IT-*` only for prevention standards |
| Accidental issues cannot be deleted | Draft mistakes become durable records too early | Allow confirmed delete/discard for accidental drafts, but use cancel/archive for durable work |
| Tags like backlog and ready-for-Codex are unclear | Lifecycle and workflow readiness are mixed | Separate issue lifecycle status from AI workflow/readiness state |
| Voice/manual rough issues need `Needs processing` | Raw intake is being forced into backlog | Add `Needs processing` as the initial AI workflow state for rough input |
| Intended flow is intake, AI analysis, backlog, Codex execution, clarification if needed | Current IA does not embody this flow | Reorder pages and states around the end-to-end workflow |
| Codex is the main operational interface | Web UI is not enough and URLs are not always deterministic | MCP tools and route URLs must expose the same service-layer workflow concepts |
| Drag and drop does not work | Board movement depends on fragile interaction | Defer drag-and-drop; ship route-backed move/apply controls that stay on Sprint Board |
| Board Apply returns to overview | The movement control breaks task context | Applying a board move must return to the selected Sprint Board view |
| Left nav order does not match workflow | Navigation is organized by feature names, not user sequence | Reorder nav by intake-to-closeout workflow |
| Board name is too generic | The page responsibility is unclear | Rename Board to Sprint Board |
| Page purpose is unclear | Pages overlap and expose raw system state | Give every page one primary job and one set of expected actions |

## Primary Users And Jobs To Be Done

The human owner needs to:

- Capture rough thoughts without polishing them first.
- See what needs processing, clarification, prioritization, implementation, verification, or closeout.
- Decide what goes into a small active sprint.
- Review evidence before accepting done or cancelled work.
- Recover context after a long session, failed run, or model handoff.

Codex and AI agents need to:

- Find the next actionable item through compact MCP tools or deterministic URLs.
- Distinguish raw intake from build-ready work.
- Know when to ask clarification questions instead of implementing.
- Read the exact acceptance criteria, proposed approach, verification commands, and STOP handoff.
- Update issue state through shared service-layer operations so web and MCP behavior do not drift.
- Preserve evidence, model/reasoning notes, and immutable terminal metadata.

## End-To-End Workflow Proposal

The recommended workflow is:

1. Capture rough input through voice recording, audio upload, or manual quick issue.
2. Create the item with workflow state `Needs processing`.
3. Codex or a human processes the raw item into a clear issue with summary, acceptance criteria, proposed approach, verification commands, model/reasoning recommendation, and STOP handoff.
4. If the issue is ambiguous, move it to `Needs clarification` and record exact questions.
5. When the issue is executable, mark it `Ready for Codex`.
6. Backlog is used for prioritization, cleanup, saved views, and sprint candidacy.
7. Sprint planning selects ready work and creates a small active sprint.
8. Sprint Board shows active sprint execution only, with route-backed status and sprint movement.
9. Verification and closeout preserve evidence, model/reasoning notes, close notes, and immutable terminal metadata.
10. Cancelled or won't-do work remains historical evidence and is excluded from delivered-work counts.

This workflow should be supported equally by the web UI and MCP. Codex should not have to scrape the UI or infer workflow meaning from labels.

## Information Architecture And Page Responsibilities

Overview is the command center. It should show only actionable rollups, next actions, and links to exact saved views. It should not be a raw aggregate dashboard.

Intake captures raw feedback. It owns voice recording, upload fallback, manual quick capture, capture errors, and creation of `Needs processing` work.

Backlog prioritizes and cleans work. It owns saved views for `Needs processing`, `Needs clarification`, `Ready for Codex`, unsprinted ready work, blocked work, and done/cancelled history.

Sprint Board executes active sprint work. It owns status movement within the active sprint and must keep the user on the board after route-backed apply actions.

Sprints plans active and upcoming work. It owns sprint creation, candidate selection, active/planned visibility, and collapsed/searchable history.

Releases owns release readiness and blockers. It should not be another all-issues view; it should answer what blocks the next release.

Categories owns taxonomy maintenance and cleanup. It is not a daily execution surface.

Issue Detail is the canonical work record. It owns processing state, lifecycle status, acceptance criteria, verification commands, evidence, dependencies, close/cancel controls, and immutable terminal metadata.

Planning, Guidance, Backup, and Admin surfaces are secondary operational surfaces. They should be discoverable but not primary workflow tabs unless the current job requires them.

## Recommended Left Navigation Order

Recommended primary order:

1. Overview
2. Intake
3. Backlog
4. Sprint Board
5. Sprints
6. Releases
7. Categories

Secondary or utility surfaces should follow after the primary workflow or sit behind a grouped utility area:

- Planning
- Guidance Sync
- Backup
- Admin or Settings

This order follows how work moves: orient, capture, process, prioritize, execute, plan/review larger batches, release, maintain taxonomy.

## Lifecycle Dashboard Recommendation

The current Lifecycle Dashboard should be replaced or reframed. The name implies a useful system view, but the UAT finding is that it exposes raw status/category noise and misleading counts.

Recommended replacement: Workflow Command Center inside Overview.

The command center should have a small number of sections:

- Intake needs action: `Needs processing` and `Needs clarification`.
- Ready to plan: `Ready for Codex`, unsprinted ready work, blocked ready work.
- Active execution: implementing, verifying, active sprint blockers.
- Closeout: ready to close, cancelled/won't-do, recently closed.

Each count must link to the exact filtered list it summarizes. If a count cannot link to a reliable filtered view, it should not appear as a count.

## Board Rename Recommendation

Rename `Board` to `Sprint Board`.

The generic name implies a full project Kanban board. The product needs a focused execution page. `Sprint Board` sets the expectation that the page is for active sprint work and route-backed movement, while Backlog remains the place for triage, prioritization, and saved views.

Drag-and-drop can remain deferred. It should not be the primary path until route-backed movement is reliable and tested.

## Workflow State Model

Workflow state should describe AI readiness and next action. It is separate from issue lifecycle status.

Recommended workflow states:

| State | Meaning | Next owner |
|---|---|---|
| `Needs processing` | Raw intake exists but has not been turned into executable work | Codex or human processor |
| `Needs clarification` | The issue cannot be safely implemented until specific questions are answered | Human owner |
| `Ready for Codex` | Summary, AC, approach, verification commands, and STOP handoff are present | Sprint planner or Codex |
| `Implementing` | Work is actively being changed | Codex |
| `Verifying` | Implementation exists and evidence is being gathered | Codex or human reviewer |
| `Closed` | Work reached a terminal lifecycle state with evidence | Historical record |

Optional future states should be added only when they remove ambiguity. For now, avoid expanding beyond the smallest set that supports the workflow.

## Lifecycle Status Versus Workflow State

Issue lifecycle/status should answer whether the record is open, in progress, complete, or intentionally not delivered.

Recommended lifecycle statuses:

- `Backlog`: open work not currently being implemented.
- `In progress`: work currently assigned to active execution.
- `Done`: delivered and verified work.
- `Cancelled` or `Won't do`: durable work record intentionally not delivered.

Workflow state should answer whether the work is raw, clarified, ready, implementing, verifying, or closed.

Examples:

- A raw voice memo is lifecycle `Backlog` and workflow `Needs processing`.
- A processed but ambiguous issue is lifecycle `Backlog` and workflow `Needs clarification`.
- A build-ready issue is lifecycle `Backlog` and workflow `Ready for Codex`.
- An active sprint issue is lifecycle `In progress` and workflow `Implementing` or `Verifying`.
- A cancelled issue is lifecycle `Cancelled` and workflow `Closed`.
- A completed issue is lifecycle `Done` and workflow `Closed`.

This distinction prevents tags like `backlog` and `ready-for-Codex` from competing as if they were the same kind of state.

## Delete, Cancel, And Archive Policy

Normal durable work should not be deleted. Once an issue has been processed, planned, implemented, referenced, assigned to a sprint, or used as decision evidence, it should be cancelled or archived rather than deleted.

Accidental drafts should have a confirmed discard/delete path:

- Allowed for raw manual drafts or failed accidental intake records before they become durable work.
- Requires a confirmation dialog or typed confirmation.
- Records a lightweight event if the record already exists in the database.
- Is not available for issues with sprint membership, dependencies, close metadata, verification evidence, or linked references.

Cancelled work remains a durable historical record:

- It keeps close/cancel metadata.
- It is excluded from delivered-work counts.
- It appears in history and saved views when intentionally requested.

Project/archive behavior should hide clutter without rewriting history.

## Category Cleanup Recommendation

Use about 5 or 6 primary project categories:

- `BUG`: user-visible broken behavior or regression.
- `FEATURE`: new user-facing capability.
- `UX`: usability, navigation, copy, accessibility, and workflow clarity.
- `OPS`: deployment, runtime, backup, observability, and configuration.
- `DOCS`: durable guidance, prompts, planning, and evidence.
- `DATA`: migrations, data cleanup, imports/exports, and state repair. If the team wants fewer categories, fold this into `OPS` and use labels for data cleanup.

Preserve `IT-1` through `IT-6` as prevention categories when standards are touched:

- `IT-1`: tracker state integrity.
- `IT-2`: category and AC binding.
- `IT-3`: schema and migration safety.
- `IT-4`: MCP contract and token discipline.
- `IT-5`: auth and secret safety.
- `IT-6`: deployment and configuration drift.

The `IT-*` categories should not dominate daily planning. They should appear when an issue touches the matching standard or when a prevention checklist must be inlined.

Existing categories should not be deleted blindly. Consolidation should be reversible and documented with a mapping table in the cleanup issue or sprint notes.

## Data Cleanup Plan

Data cleanup should be its own planned phase after the user approves the product direction.

Recommended cleanup steps:

1. Snapshot current category, issue, sprint, workflow, status, and count data before mutation.
2. Define the approved category mapping from old categories to the new primary taxonomy.
3. Preserve `IT-*` categories and checklist behavior for standards-sensitive work.
4. Backfill raw voice, audio, intake, `To process`, and rough manual issues to `Needs processing`.
5. Backfill ambiguous or blocked-on-question items to `Needs clarification` only when explicit questions exist or can be safely derived.
6. Backfill processed executable backlog items to `Ready for Codex` only when AC, proposed approach, verification commands, and STOP handoff exist.
7. Mark stale active sprint memberships for review before closing or removing them.
8. Move closed sprint history out of default views while preserving access.
9. Recompute dashboard counts and verify every count drills into the exact matching issue list.
10. Record cleanup evidence in durable markdown and tracker closeout metadata.

Cleanup should be performed through service-layer operations or reviewed migrations, not ad hoc database edits.

## Performance And Perceived-Wait Plan

The immediate goal is not world-class performance. The goal is to make the app feel trustworthy and prevent the user from thinking it is frozen.

Recommended targets:

- Primary navigation acknowledges the click within 100 ms through active, disabled, pending, or busy state.
- Normal page transitions usually complete within 1 to 2 seconds on the local deployment.
- Heavier dashboard/report pages may take up to 3 seconds only if they show visible loading or busy state.
- Anything likely to exceed 3 seconds needs progress feedback, a cheaper default query, pagination, caching, or a drill-down design.
- Route-backed form submits should disable the submitting control and preserve the destination context.

Cost/benefit guidance:

- Prefer cheaper default queries, pagination, saved filters, and fewer aggregate widgets before adding broad indexes.
- Add indexes only after observing high-value query patterns, such as project/status/workflow/sprint/category/milestone filters.
- Document storage and write-cost tradeoffs before adding indexes.
- Measure or inspect query cost before treating indexes as the fix for unclear dashboard design.

For the UAT failures, visible feedback and better page defaults should come before database tuning.

## Dashboard And Count Drill-Down Rules

Every count is a navigation promise.

Rules:

- A count must link to the exact filtered issue list, sprint board, release list, or history view it summarizes.
- The destination must show the active filter visibly.
- Empty results must explain the selected filter and next action.
- Counts must not mix lifecycle status and workflow state unless the label says exactly what is being counted.
- Done and cancelled/won't-do must not be combined in delivered-work counts.
- Dashboard totals should be small enough to answer "what should I do next?"
- If the count is expensive or ambiguous, remove it from the default view and provide a saved report instead.

## Route-Backed Board Movement

Sprint Board movement should be reliable without drag-and-drop.

Requirements:

- Each move/apply control posts to a route-backed operation using the shared service layer.
- The operation returns to the same Sprint Board context, including selected sprint and filters.
- The UI shows pending/disabled state during submit.
- Service and route tests prove the issue moved and the response stays on the board.
- Drag-and-drop remains a future enhancement until the route-backed path is complete and tested.

## Codex Prompt README Recommendation

Large prompts should include a cleanup preflight before execution:

- Check dirty worktree state and list unrelated changes.
- Confirm the prompt has acceptance criteria, verification commands, model/reasoning recommendation, files in scope, and STOP handoff.
- Query tracker and durable markdown only when the prompt authorizes tracker/database access.
- For planning-only prompts, explicitly state that tracker issues, sprints, schema changes, and implementation are out of scope.
- Record any model/reasoning mismatch in the produced artifact or handoff.

This recommendation should be added to prompt guidance after this six-pager is approved, not as part of this planning-only prompt.

## Draft User Stories By Phase

Phase 1: Product spine and state model

- As a human owner, I can see a clear workflow from rough intake to verified closeout so I know where each issue belongs.
- As Codex, I can distinguish lifecycle status from workflow readiness so I do not implement raw or ambiguous input.
- As a planner, I can review a concise state model before approving schema or UI changes.

Phase 2: Intake and processing

- As a human owner, I can record or upload feedback and see immediate recording, upload, error, and saved states.
- As Codex, I can find `Needs processing` items and convert them into clear issues with AC, approach, verification, and STOP handoff.
- As a human owner, I can answer exact clarification questions before work moves to `Ready for Codex`.

Phase 3: Backlog and command center

- As a human owner, I can use saved views for `Needs processing`, `Needs clarification`, `Ready for Codex`, unsprinted ready work, blocked work, and history.
- As Codex, I can open deterministic URLs that reproduce the same filtered view.
- As a human owner, I can click any Overview count and land on the exact matching filtered list.

Phase 4: Sprint execution

- As a sprint planner, I can select a small ready batch without seeing all historical work by default.
- As Codex, I can move active work through implementing and verifying through shared service-layer operations.
- As a human owner, I can use route-backed board controls that stay on Sprint Board after apply.

Phase 5: Cleanup and closeout

- As a human owner, I can discard accidental raw drafts but cancel durable work records with preserved metadata.
- As a maintainer, I can consolidate categories without losing issue history or `IT-*` prevention behavior.
- As a reviewer, I can verify that done work has evidence and cancelled work is excluded from delivered counts.

Phase 6: Performance and UAT proof

- As a human owner, I can tell whether the app is navigating, saving, recording, or waiting.
- As a tester, I can run browser/manual UAT that proves the core intake-to-closeout workflow.
- As a maintainer, I can justify any new indexes with observed query patterns.

## Proposed Sprint Phases

These are planning phases only. Do not create or start tracker sprints until the six-pager is reviewed and approved.

Sprint phase A: Workflow model and information architecture

- Finalize lifecycle status versus workflow state.
- Finalize page responsibilities and nav order.
- Write user stories and acceptance criteria.
- Decide whether workflow state is schema-backed immediately or staged through existing metadata first.

Sprint phase B: Intake trust and `Needs processing`

- Fix recording state feedback and upload fallback.
- Add or expose `Needs processing`.
- Add raw intake saved view and MCP search path.
- Add accidental draft discard policy.

Sprint phase C: Backlog and Overview command center

- Replace Lifecycle Dashboard with workflow command center.
- Add exact drill-down rules and tests.
- Add saved workflow views and visible filter state.
- Reduce all-work default counts.

Sprint phase D: Sprint Board and execution controls

- Rename Board to Sprint Board.
- Make route-backed apply controls stay on the board.
- Constrain default board to active sprint execution.
- Defer drag-and-drop explicitly.

Sprint phase E: Category and data cleanup

- Approve category mapping.
- Backfill workflow states.
- Clean stale sprint visibility.
- Preserve `IT-*` prevention behavior.
- Verify dashboard count sanity after cleanup.

Sprint phase F: Verification and UAT

- Add browser/route coverage for intake, saved views, count drill-downs, Sprint Board movement, delete/cancel behavior, and perceived-wait states.
- Run manual UAT through setup/login/project/issue/intake/backlog/sprint/board/closeout.
- Record pass/fail evidence and remaining STOP handoff.

## Future Redesign Acceptance Criteria

Pass criteria for the future redesign:

- Raw voice, upload, and manual quick capture create visible `Needs processing` work.
- Ambiguous work can move to `Needs clarification` with exact questions.
- Executable work cannot be called `Ready for Codex` unless it has summary, AC, approach, verification commands, and STOP handoff.
- Lifecycle status and workflow state are distinct in labels, filters, MCP output, and issue detail.
- Overview counts are actionable and drill into exact filtered views.
- Lifecycle Dashboard is removed, renamed, or reframed so it no longer exposes noisy raw aggregates by default.
- Board is renamed `Sprint Board`.
- Sprint Board movement is route-backed, tested, and returns to the selected board context.
- Drag-and-drop is either deferred or implemented only after route-backed movement passes.
- Backlog saved views include `Needs processing`, `Needs clarification`, `Ready for Codex`, unsprinted ready work, blocked, done, and cancelled history.
- Categories are consolidated to about 5 or 6 primary categories while preserving `IT-*` prevention categories.
- Accidental raw drafts can be discarded with confirmation; durable work uses cancel/archive.
- Done and cancelled/won't-do are separated in counts, filters, and closeout evidence.
- Primary navigation shows immediate feedback and slow pages show busy/progress state.
- MagicPatterns-derived UI structure is preserved unless a targeted, documented workflow change requires adjustment.

## Verification Strategy

Planning verification:

- The six-pager is reviewed by the user before issue creation, sprint planning, schema changes, or implementation.
- Follow-up user stories include pass/fail acceptance criteria, verification commands, model/reasoning recommendation, and STOP handoff.

Implementation verification after approval:

- Service tests cover workflow state transitions, lifecycle status transitions, delete/cancel policy, category mapping, and terminal metadata.
- Route tests cover saved views, count drill-downs, Sprint Board movement, and filtered destinations.
- MCP tests cover compact workflow-aware search/list output and parity with service behavior.
- Browser/manual UAT covers recording feedback states, navigation wait states, Overview drill-downs, Backlog saved views, Sprint Board movement, issue close/cancel, and mobile/desktop usability.
- Data cleanup verification records before/after counts and sample issue checks for each mapping.
- Performance verification records observable slow routes before adding indexes.

Manual UAT expectations:

- Browser pages are visibly styled and usable.
- Text and controls do not overlap.
- Every primary page has an obvious job.
- Clicking a count or saved view lands on a visibly filtered page.
- Recording or upload controls show state immediately.
- Applying movement on Sprint Board keeps the user on Sprint Board.

## Risks, Tradeoffs, And Open Questions

Risk: Adding workflow state may require schema changes, service updates, MCP contract updates, and data backfill. Mitigation: approve the model first, then implement through a migration and service-layer tests.

Risk: A product reset could accidentally rewrite the protected MagicPatterns UI. Mitigation: preserve layout, spacing, visual hierarchy, labels, and component structure unless the approved story names a targeted change.

Risk: Category cleanup could damage history. Mitigation: use a reversible mapping, preserve old labels or events where needed, and verify sampled records.

Risk: Too many states could recreate the same noise problem. Mitigation: keep the workflow states to the six listed states until dogfooding proves another state is necessary.

Risk: Dashboard redesign could hide useful data. Mitigation: move noisy aggregates to saved reports or drill-down pages rather than deleting the underlying data.

Risk: Performance work could become premature indexing. Mitigation: add wait feedback and cheaper default views first; add indexes only after observed query cost.

Open questions:

- Should workflow state become a first-class column immediately, or should the first implementation phase prove it through existing metadata?
- Should `DATA` be a sixth primary category, or should data cleanup live under `OPS` with labels?
- What exact confirmation should be required for accidental draft delete?
- Should cancelled and won't-do be one lifecycle status with two close reasons, or separate statuses?
- Which MCP tool should become the canonical "next raw intake item" path?
- Should the active sprint be limited to only `Ready for Codex` work, or can `Needs clarification` enter a sprint as blocked discovery work?

## STOP

Stop here for user review. Do not create user stories as tracker issues, create or start tracker sprints, change schema, implement UI/code changes, run data cleanup, mutate tracker data, deploy, or perform destructive actions until the user reviews and approves this six-pager.
