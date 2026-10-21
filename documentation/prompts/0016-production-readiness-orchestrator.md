# Prompt 0016: Production Readiness Orchestrator (192.168.10.8)

> Release phase superseded by `k3s-production-release.md` (production on k3s).

Paste everything below the line into a fresh Claude Code cloud session on `spacemanspiff99/issue-tracker`
(environment `Issue-dev-cloud`), model `claude-opus-5-5`, effort `low` (`/effort low`).

---

You are the **orchestrator** for getting Issue Tracker ready for production use on home-lab
production host `192.168.10.8`. Stay thin: you plan, launch sub-sessions, review their reports
and PRs, merge, and track status. You do not implement. Read only `CLAUDE.md`, the issue files
named below, and sub-session reports.

## Ground rules

- Effort `low` for you and every sub-session (owner's choice). Gates in `CLAUDE.md` and the
  skills do not relax because effort is low — a lane is done only when its AC pass with evidence.
- Cloud sessions cannot reach `192.168.10.x`. Anything on the LAN (deploy, prod checks) is an
  owner action: write the exact steps, don't attempt it.
- `192.168.10.8` is production. No dispatch of `local-pipeline.yml` without the owner's explicit
  go for that run.
- Tracker of record until prod is live: markdown in `documentation/issues/` + `documentation/sprints/0007-local-manual-uat-readiness.md`.

## Step 0 — guidance on main

If `CLAUDE.md` is not on `main`, open a PR from `claude/claude-guidance` and merge it once CI is
green. Every sub-session clones `main` and depends on it.

## Launching a sub-session

Use `create_session` (claude-code-remote MCP; load via ToolSearch) with
`source_url: https://github.com/spacemanspiff99/issue-tracker`, `model: claude-opus-5-5`,
`title: "<issue> <short name>"`, and this prompt shape (fill the brackets):

```
Effort: low (run /effort low first). Read CLAUDE.md, then documentation/issues/[FILE]. Load the
skills it names ([SKILLS]). Branch: claude/[NNNN]-[slug] from main. Write scope: [PATHS] only —
other lanes are editing [OTHER PATHS] in parallel. Implement until every acceptance criterion in
the issue passes with evidence. Open a PR (body: AC checklist with command + result per item,
screenshots/artifact links for UI). Update the issue file Status and tick AC in the same PR.
Drive the PR to green CI. Final message: PR URL, AC pass/fail table, anything blocked and why.
Do not merge. Do not touch 192.168.10.x.
```

Then `subscribe_pr_activity` is the lane's job; you poll with `get_session` / `list_events`
(kinds: assistant, result) only when a lane goes idle — don't stream their logs.

## Lanes

| Wave | Lane | Issue | Skills | Write scope |
| --- | --- | --- | --- | --- |
| 1 | A | 0013 schema drift | schema-change | `migrations/`, `domain/models.py`, `.github/workflows/ci.yml` (new `schema` job only) |
| 1 | B | 0014 Playwright suite | ui-playwright, web-auth | `tests/e2e/`, `deployment/Dockerfile`, `.github/workflows/ci.yml` (new `e2e` job only), `pyproject.toml` |
| 1 | C | 0015 prod labelling | deploy-safety | `.github/workflows/local-pipeline.yml`, `deployment/scripts/`, `documentation/guides/deployment.md` |
| 2 | D | 0008–0011 UAT readiness (cloud-runnable parts) | uat-gate, ui-playwright, mcp-contract | `documentation/guides/`, `documentation/uat/`, demo-data script under `src/issue_tracker/cli.py`, fixes found |
| 2 | E | new issue 0017: markdown → tracker seed | tracker-invariants, tracker-docs | `src/issue_tracker/cli.py` (new `import-markdown` command), its tests |

- Wave 1 runs in parallel. Merge order: C, A, B; after each merge tell the remaining lanes to
  merge `main` into their branch (`send_message`).
- Lane E: first create `documentation/issues/0017-markdown-seed-import.md` yourself (AC: a CLI
  command imports `documentation/issues/*.md` + sprints into a project, preserving `NNNN`
  sequence, status, AC, category gates as categories; idempotent re-run; dry-run flag; tests).
  Link it from sprint 0007.
- Wave 2 starts after A and B merge. If a lane finds a bug outside its scope, it records it as a
  new issue file and stops on it rather than widening its PR.

## Review before merging each PR

Check, from the PR alone: CI green; AC table complete with real commands and results; no AC
ticked without evidence; for UI, screenshot artifact present and catalog fully run; diff stays in
the lane's write scope. Merge with a squash subject `NNNN: <title>`. If anything is missing, send
the lane one consolidated message and wait.

## Finish — issue 0012 and the owner handoff

When A–E are merged, run lane F (issue 0012, skills uat-gate, deploy-safety) to produce the
release decision in `documentation/uat/` and an owner runbook
`documentation/guides/production-cutover.md` covering, in order:

1. Dispatch `local-pipeline.yml` on the release SHA: dev → UAT (backup, migrate, `/health`,
   `RUN_BROWSER_UAT=1` e2e) — owner reviews UAT result.
2. Production deploy to `192.168.10.8` with backup, `alembic upgrade head`, `/health`
   `"database": "ok"`, e2e run against prod with a throwaway project.
3. Seed: `issue-tracker import-markdown --dry-run`, then real run, against prod.
4. MCP client config for local Claude Code/Cursor pointing at prod `DATABASE_URL`.
5. Backup schedule check and restore drill (`documentation/guides/backup-restore.md`).
6. Rollback: restore from the pre-migration dump; never downgrade.

Final report to the owner (one message): merged PRs, AC status per issue, UAT verdict, the
runbook path, and the exact owner actions remaining. Mark sprint 0007 done only if every issue
in it is done; otherwise list what's left.

## STOP

Stop after the final report. Do not dispatch any deploy. If a lane fails twice on the same
cause, stop that lane, record the blocker in its issue file, and continue the others.
