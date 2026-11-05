---
name: sprint-closeout
description: Close out an issue, sprint, or execution prompt. Reconciles tracker state with markdown, checks acceptance criteria and IT-category gates, records evidence, and writes the STOP handoff. Use when finishing work, closing issues, or when the user asks for a handoff or wrap-up.
---

# Issue / Sprint Closeout

Source of truth: `AGENTS.md` (Dual Tracker Dogfooding; Issues, Prompts, And STOP Handoffs; Acceptance Criteria; Evidence And Closeout) and `documentation/standards/ISSUE_LOG.md`.

## 1. Gather state

- Tracker: use the `issue-tracker` MCP tools (`sprint.get`, `issue.search`, `issue.get` with full detail only for issues being closed) to list every issue in scope and its status.
- Markdown: the matching `documentation/sprints/NNNN-*.md`, `documentation/issues/NNNN-*.md`, or `documentation/prompts/NNNN-*.md`.
- Repo: `git status --short`, `git log --oneline dev..HEAD`.

If an item exists in only one system and matters beyond the local DB, add the missing side.

## 2. Verify each issue against its AC

For every issue being closed:

- Each AC item has a pass/fail result with evidence (test name, command output, screenshot path, run URL).
- If the work touched an `IT-1`..`IT-6` category, the matching prevention checklist from `ISSUE_LOG.md` is inlined and checked.
- Schema changes: `alembic upgrade head` passed on an empty DB.
- UI changes: browser or route-level proof the page is styled and usable.
- MCP changes: compact output shape and error behavior are tested.

Any AC without evidence means the issue stays open. Do not close it.

## 3. Close in the tracker

Use `issue.update_status` to close each passing issue. Keep immutable close metadata: actor (`claude-code` plus model), timestamp, and commit SHA or PR reference. Add an issue-log entry if the fix maps to a recurring category.

## 4. Update markdown

Update the sprint, issue, or prompt file with the final status, evidence, and remaining list. New docs must be linked from somewhere discoverable (no orphans). Use `NNNN` four-digit IDs.

## 5. STOP handoff

End with a `## STOP` section. For a large sprint it must say exactly one of:

- the sprint is complete and closed;
- the sprint is blocked by a specific owner action (name it); or
- the user explicitly accepted named deferrals (list them).

"Next slice is ready" alone is not acceptable. Also report: changed files, verification commands and results, blocked checks, uncommitted files, and confirmation that no secrets, `.env` files, dumps, or large artifacts were added.
