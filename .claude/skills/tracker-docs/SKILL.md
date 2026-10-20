---
name: tracker-docs
description: Use when creating, updating, or closing an issue, sprint, or execution prompt under `documentation/` (issues/, sprints/, prompts/), writing acceptance criteria, recording a recurring bug in `documentation/standards/ISSUE_LOG.md`, or adding any new doc. Covers the shared NNNN ID sequence, required AC with IT-category checklists, STOP sections, close metadata, and no-orphan docs.
---

# Tracker Docs

Until the app dogfoods itself, this repo's own tracker is markdown in `documentation/`.

## IDs and files

- Issues and sprints share one `NNNN` sequence. Next ID = highest number across
  `documentation/issues/` and `documentation/sprints/` + 1 (Glob both folders;
  never trust a remembered number). Files: `NNNN-kebab-title.md`.
- Header lines: `# Issue NNNN: Title`, `Status: backlog|in-progress|done`, `Recommended model:`
  (Claude sessions: e.g. `claude-opus-5-5 medium`), `Category gates:` (`IT-n` list), `Sprint: Sprint NNNN`.

## Issue body (keep it short)

Context (2–4 lines) · Files in scope · Acceptance criteria as `- [ ]` pass/fail items ·
Category gates (paste the matching `IT-n` checklist line verbatim from `ISSUE_LOG.md`) ·
Verification commands · `## STOP` (when to stop, or the exact blocker + next step).
Copy an existing issue in `documentation/issues/` as the template rather than inventing one.
UI issues: AC must be Playwright workflows with step-level expected results and test names
(`ui-playwright` §1) — an issue without them isn't ready to start.

## Closing

Set `Status: done`; tick AC with evidence (command + result, commit SHA/PR). Record the
originating model (e.g. `claude-opus-5-5 (effort: medium)`). Never close with a failing or
skipped gate — record it under STOP instead.

## Recurring bug → ISSUE_LOG

If a fixed bug matches a pattern seen before, add a row to the `## Log` table (date, issue,
`IT-n`, root cause, prevention added) and put the prevention in the owning skill or `.claude/rules/`
file in the same change (`guidance-change`). New category only if no `IT-n` fits.

## No orphans

Every new doc is linked from README, a planning doc, a sprint, or an issue.
