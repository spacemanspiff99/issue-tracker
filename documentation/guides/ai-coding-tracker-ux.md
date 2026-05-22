# AI Coding Tracker UX Principles

Linked sprint: `documentation/sprints/0050-backlog-ux-release-voice-feedback-playwright.md`

## Research Inputs

- Linear: fast keyboard-oriented issue navigation, cycles, views, triage, and compact side panels.
- GitHub Projects: flexible saved views, field-driven planning, milestone/release rollups, and direct repository linkage.
- Trello: simple board movement, visual work-in-progress scanning, and low-friction backlog ordering.
- ClickUp: cross-cutting spaces, dashboards, custom fields, and intake forms, with a high risk of feature sprawl.

## Product Principles

1. Keep the issue as the canonical unit of AI work. Sprints, releases, boards, and intake views should roll up or route issues instead of inventing parallel task records.
2. Use field-driven planning before schema expansion. Milestones, workflow state, readiness notes, labels, and custom fields can live in issue metadata while dogfooding proves the shape.
3. Optimize for handoff quality. Every intake and backlog item should make clear whether it is rough input, needs clarification, ready for Codex, implementing, verifying, or closed.
4. Prefer compact, scannable work surfaces. Saved views, sprint filters, release rollups, and sidebars should reduce page switching without hiding acceptance criteria and evidence.
5. Preserve accessible fallbacks. Drag-and-drop can improve ordering, but every movement must also have route-backed form controls.
6. Treat local artifacts as private evidence. Audio, screenshots, exports, and backups stay in ignored paths, while committed docs record only summaries and commands.

## Sprint 0050 Application

- Top-level project tabs expose Overview, Backlog, Board, Releases, Intake, Planning, and Backup.
- Release planning uses issue milestone metadata and readiness custom fields to roll up progress across sprints.
- Sprint boards default to the active sprint, support single or multi-sprint filters, and still show assignment controls for backlog issues.
- Voice feedback is intake-first: it stores audio in ignored local artifacts, creates a backlog issue, and marks ambiguous reports as `clarify`.
- Issue detail keeps fast status, workflow, sprint assignment, metadata, dependency, reference, and closeout controls visible with a responsive sidebar.
