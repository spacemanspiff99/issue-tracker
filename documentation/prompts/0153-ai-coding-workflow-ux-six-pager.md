# Prompt: AI Coding Workflow UX Six-Pager

Use this prompt in a fresh Codex session. Do not continue in the same session that created this prompt.

## Objective

Create an Amazon-style six-pager that rethinks Issue Tracker around its real job: turning rough human input into clear, executable Codex work, then preserving enough state and evidence to plan, execute, verify, and close that work safely.

Stop after the six-pager is written. Do not implement code changes, do not create the follow-up tracker issues, do not start a sprint, and do not change the database. The user wants to read and approve the six-pager before proceeding to user stories, issue creation, sprint planning, or implementation.

## Repository

Repository: `/home/akun/issue-tracker`

This repo is a FastAPI, Jinja, SQLAlchemy 2.x, Alembic, PostgreSQL, and MCP application. It is not a generic Jira clone. It is a local-first tracker for steering AI coding work.

## Required Model And Reasoning

Recommended model/reasoning: GPT-5.5 `high`.

Use high reasoning because this is product architecture and information architecture work that will later affect schema, workflow states, web routes, MCP contracts, data cleanup, and manual UAT expectations.

If GPT-5.5 is unavailable, use the strongest available model and record the mismatch in the six-pager handoff.

## Source Context

Read these files first:

- `AGENTS.md`
- `README.md`
- `documentation/guides/product-guide.md`
- `documentation/guides/ai-coding-tracker-ux.md`
- `documentation/guides/issue-tracker-ux-flow-map.md`
- `documentation/sprints/0140-urgent-usability-rescue.md`
- `documentation/guides/manual-uat.md`
- `documentation/design/magicpatterns/UI.tsx`

Treat `documentation/design/magicpatterns/UI.tsx` as protected source design. The six-pager may recommend product structure changes, labels, workflow changes, and targeted UX changes, but it must not casually restyle or replace the MagicPatterns UI without naming why a specific change is necessary.

## Manual UAT Readout To Address

The user reported:

- On issue overview, clicking Voice Intake, then Record Audio appears to do nothing: no recording state, no error, no feedback.
- Navigation feels frozen because page loads are slow or give no wait/progress feedback.
- Lifecycle Dashboard shows counts such as 16 implementing, but clicking the link lands on a safe view with no matching issues or no visible filter.
- Lifecycle Dashboard is not useful because it exposes too much raw status/category noise.
- Active sprint and overview surfaces show very large counts, such as 140 issues, without helping the user decide what to do.
- There are too many categories; the useful default taxonomy should be about 5 or 6 categories.
- Creating a new issue works and it appears in backlog, but there is no delete path for accidental issues.
- Issue sidebar tags such as backlog and ready-for-Codex do not clearly distinguish rough intake from processed, build-ready work.
- Voice memos and manually created rough issues need an obvious `Needs processing` state before Codex analysis.
- The intended workflow is: intake rough feedback, AI analyzes and flushes out the issue, issue moves to backlog, then Codex executes; if more clarity is needed, Codex asks questions.
- Codex is the main operational interface, not only the web UI.
- Drag and drop on the board does not work, but a reliable route-backed move/apply control is acceptable for now.
- Moving an issue from the board with Apply returns to overview; it should remain on the board.
- Left nav tabs should be ordered by workflow use.
- `Board` should be renamed `Sprint Board`.
- The purpose of each page is unclear; every page needs a specific job in the end-to-end workflow.
- The user explicitly wants a product-management reset: first define the workflow, then write an Amazon-style six-pager, then build user stories, issues, and sprints.

User clarifications:

- Yes, this can be a true product and information architecture reset, including deprecating or renaming current surfaces like Lifecycle Dashboard and Board.
- For delete behavior, follow the best recommendation: normal work should be cancel/archive-oriented, but accidental draft/manual issues need a confirmed delete or discard path.
- Yes, include data cleanup: category consolidation, workflow labels, stale sprint cleanup, and `Needs processing` backfill.
- Performance does not need to be world class. The immediate problem is that the user cannot tell whether the app is waiting or frozen. Define reasonable usability targets and prefer low-cost feedback states before expensive indexing. Indexes should be justified by observed query cost and not require large storage or memory tradeoffs without evidence.
- Drag-and-drop is not required for now. Reliable route-backed move/apply controls are acceptable.

## Product Direction To Evaluate

The six-pager should evaluate and refine this proposed workflow:

1. Capture rough input through voice intake, upload, or manual quick issue.
2. Mark raw items as `Needs processing`.
3. Codex or a human processes the raw item into a clear issue with summary, acceptance criteria, proposed approach, verification commands, and STOP handoff.
4. If the issue is ambiguous, move it to `Needs clarification` and record exact questions.
5. When the issue is executable, mark it `Ready for Codex`.
6. Backlog is used for prioritization, cleanup, and sprint candidacy.
7. Sprint planning selects ready work and creates a small active sprint.
8. Sprint Board shows active sprint execution only, with route-backed status and sprint movement.
9. Verification and closeout preserve evidence, model/reasoning notes, and immutable terminal metadata.
10. Cancelled or won't-do work remains historical evidence and is not mixed into delivered work.

## Six-Pager Requirements

Create a new planning document at:

`documentation/planning/AI_CODING_WORKFLOW_UX_SIX_PAGER.md`

The document must include:

- Title, date, authoring context, and explicit status: `Draft for user review`.
- Executive summary.
- Press-release style future-state narrative.
- Customer problem and current UAT failure analysis.
- Primary users and jobs-to-be-done, including the human owner and Codex/AI agent.
- End-to-end workflow proposal from intake through closeout.
- Proposed information architecture and page responsibilities.
- Recommended left navigation order.
- Recommendation for replacing, removing, or reframing Lifecycle Dashboard.
- Recommendation for renaming Board to Sprint Board.
- Recommended workflow state model, including at least `Needs processing`, `Needs clarification`, `Ready for Codex`, `Implementing`, `Verifying`, and terminal states.
- Recommended issue lifecycle/status distinction from workflow state.
- Delete, cancel, and archive policy for accidental drafts versus durable work records.
- Category cleanup recommendation with about 5 or 6 primary categories, plus how to preserve `IT-*` prevention categories when standards are touched.
- Data cleanup plan covering category consolidation, stale sprints, raw intake backfill, issue labels/workflow states, and dashboard count sanity.
- Performance and perceived-wait plan with pragmatic targets and cost/benefit guidance.
- Dashboard/count drill-down rules: every count must link to the exact filtered issue list it summarizes.
- Route-backed board movement requirement and current deferral of drag-and-drop.
- Codex prompt README recommendation for cleanup before running large prompts.
- User stories grouped by phase, but do not create actual tracker issues yet.
- Proposed sprint phases, but do not create or start actual sprints yet.
- Acceptance criteria for the future redesign.
- Verification strategy, including browser/manual UAT expectations.
- Risks, tradeoffs, and open questions.
- Explicit STOP section saying user review is required before user stories, tracker issues, sprints, schema changes, or implementation.

## Proposed Page Responsibilities To Consider

Use or improve this structure:

- Overview: command center with only actionable rollups and next actions.
- Intake: capture raw feedback and create `Needs processing` work.
- Backlog: prioritize and clean work; show saved views such as Needs Processing, Needs Clarification, Ready for Codex, Unsprinted Ready Work, Blocked, and Done/Cancelled history.
- Sprint Board: execute active sprint work only; route-backed movement stays on the board.
- Sprints: plan active and upcoming sprints; history is secondary.
- Releases: release readiness and blockers only.
- Categories: taxonomy maintenance and cleanup, not day-to-day work.
- Issue Detail: canonical work record with processing state, AC, verification, evidence, dependencies, and close/cancel controls.
- Planning/Guidance/Backup/Admin surfaces: secondary operational surfaces, not primary workflow tabs.

## Performance Guidance

Define reasonable usability targets in the six-pager. Suggested starting point:

- Primary navigation should show immediate visual feedback within 100 ms.
- Normal page transitions should usually complete within 1 to 2 seconds on the local deployment.
- Heavier dashboard/report pages may take up to 3 seconds if they show a visible loading or busy state.
- Anything likely to exceed 3 seconds needs either visible progress, a cheaper default query, pagination, caching, or a drill-down design.
- Add indexes only after identifying high-value query patterns, such as project/status/workflow/sprint/category/milestone filters, and call out the storage/write-cost tradeoff.
- Prefer pagination, filtered defaults, and removing noisy aggregate widgets before adding broad indexes.

You may adjust these targets if the six-pager explains the reasoning.

## Files In Scope

Planning-only edits:

- `documentation/planning/AI_CODING_WORKFLOW_UX_SIX_PAGER.md`
- `README.md` only to add a discoverability link to the new six-pager.
- `documentation/planning/PROJECT_PLAN.md` only if needed to avoid orphan documentation.

Do not edit application code, migrations, tests, templates, CSS, deployment scripts, or tracker data in this prompt.

## Acceptance Criteria

- The six-pager exists at `documentation/planning/AI_CODING_WORKFLOW_UX_SIX_PAGER.md`.
- The six-pager is discoverable from `README.md` or `documentation/planning/PROJECT_PLAN.md`.
- The six-pager directly addresses every UAT failure and user clarification above.
- The six-pager stops before implementation and before actual tracker issue/sprint creation.
- The document contains a clear product recommendation, not just a list of bugs.
- The document separates issue lifecycle/status from AI workflow/readiness state.
- The document includes a pragmatic perceived-performance plan and avoids recommending expensive indexes without evidence.
- The document includes future user stories and sprint phases only as draft planning material.
- The final response asks the user to review the six-pager before proceeding.

## Verification Commands

Run the smallest relevant validation:

```bash
python -m compileall src/issue_tracker
git status --short documentation/planning/AI_CODING_WORKFLOW_UX_SIX_PAGER.md README.md documentation/planning/PROJECT_PLAN.md
```

If `compileall` is blocked by the local environment, report the exact failure. Do not install missing system packages or dependencies.

## STOP

Stop after writing the six-pager and linking it from a discoverable document. Do not proceed to user stories as tracker issues, sprint creation, schema changes, implementation, data cleanup, deployment, or destructive actions until the user reviews and approves the six-pager.
