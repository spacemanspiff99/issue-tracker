# Issue Tracker — Claude Code Core

Always-loaded layer: project facts, tripwires, and a skill index. Path-scoped invariants live in
`.claude/rules/` (auto-load when you touch matching files); procedures live in `.claude/skills/`
(load the named skill before doing that work). Layout rationale: `.claude/README.md`.

## Project

Personal issue tracker replacing repo-local markdown trackers. One Python service:
FastAPI + Jinja (server-rendered, no React/Next) + SQLAlchemy 2.x + Alembic + PostgreSQL, plus a
stdio MCP server. Web routes and MCP tools are thin adapters over one service layer.

```
src/issue_tracker/  domain/models.py  repositories/store.py  services/tracker.py
                    web/app.py + templates/  mcp/tools.py + server.py  cli.py  config.py
migrations/versions/   tests/unit/ tests/integration/   deployment/   documentation/
```

Scope: `documentation/planning/MVP_SCOPE_LOCK.md` (non-MVP asks go to backlog, not into the
active slice). `documentation/planning/PROJECT_PLAN.md` is ~480 lines — grep it, don't read it whole.

## Commands

Fast gate (same as CI `test` job; run before every commit):

```bash
pip install -e ".[dev]"          # ephemeral/cloud container only; once per session
python -m ruff check . && python -m pytest -q tests
```

Tests use in-memory SQLite via `Base.metadata.create_all` — they do **not** exercise Alembic or
Postgres. Schema work needs the Postgres check in `schema-change`. Canonical local runtime is
Docker Compose (`deployment/docker-compose.local.yml`); host Python is fine only in throwaway
containers, never as a documented user-facing path.

## Operating defaults

- **Model/effort.** `medium` for routine code, tests, docs. `high` for schema/migrations, auth,
  deploy, MCP contract changes, UAT release decisions, debugging that can corrupt tracker state.
  Subagents: only for noisy or parallel work (CI log digs, Playwright sweeps, broad searches);
  `sonnet` for evidence collection, verdicts stay on the main model.
- **Token discipline.** Grep/Glob before Read; read the section you need, not the file. Don't
  re-read files you just edited. Don't paste long logs — quote the failing lines.
- **Assume, execute, report once.** Sensible default or findable answer → choose, act, note the
  assumption in the commit/PR. Never assume past an approval gate (deploy, prod data,
  destructive ops, secrets). End with one report: changed files, commands run + results,
  blockers, assumptions.
- **Harness boundaries.** `CLAUDE.md` + `.claude/` are Claude's guidance. `AGENTS.md`, `.codex/`,
  `.cursor/` belong to Codex/Cursor: read for facts if useful, don't edit unless asked.
  `spacemanspiff99/vibecoding` receives mirrors only — never hand-edit there.
- **Git.** Single `main` branch. Work on a feature branch, one behavior change per PR. Run
  `git branch --show-current` before committing. Don't revert unrelated dirty-worktree changes.

## Tripwires

- **One service layer.** Lifecycle, validation, and sequence logic live in `services/`. Never
  duplicate it in routes, templates, or MCP tools. → `tracker-invariants`
- **Schema = model + migration + Postgres check.** Every model change ships an Alembic revision
  in `migrations/versions/` (the only migration tree) and passes `alembic upgrade head` on an empty
  Postgres. App startup never migrates, drops, or truncates. → `schema-change`
- **Project-scoped taxonomy.** Categories are per-project data. Never hardcode `IT-*`, `CAT-*`,
  `WEA-*` or any peer project's names in app logic. → `tracker-invariants`
- **MCP output is compact by default**; full text/AC opt-in by ID; logs to stderr only. →
  `mcp-contract`
- **Secrets.** No `.env`, credentials, dumps, backups, or exports in git. Passwords Argon2-hashed;
  session cookie HTTP-only + SameSite=Lax. → `web-auth`
- **Deploys need explicit user approval.** `192.168.10.8` is home-lab **production** (the
  pipeline mislabels it `dev_host`); `.18` UAT, `.20` dev. Backup
  before migrate; never downgrade/drop/reset in a release. `/health` must show DB connectivity.
  → `deploy-safety`
- **UI = Playwright workflows.** Any visible change: AC written as workflows, Playwright drives
  the full workflow catalog in `tests/e2e/`, screenshot at every step, assertions per step. →
  `ui-playwright`
- **Truth.** Never say "done" or "ready for UAT" without the gate's commands actually passing on
  this commit. A green unit run is not a migration check or a browser check. → `uat-gate`
- **Two failures, same cause → stop** and gather new evidence before retrying.

## Skill index

| When you are… | Load |
| --- | --- |
| Changing `domain/models.py`, adding/editing a migration, DB constraints | `schema-change` |
| Changing services, repositories, sequence IDs, status, dependencies, close metadata, categories | `tracker-invariants` |
| Adding/changing an MCP tool, its args, or its output shape | `mcp-contract` |
| Changing routes, templates, setup/login, sessions | `web-auth` |
| Any visible UI change, writing UI acceptance criteria, or claiming a UI works | `ui-playwright` |
| Touching `deployment/`, compose, Dockerfile, workflows, env vars, backups, or running a deploy | `deploy-safety` |
| Writing/closing an issue, sprint, or prompt in `documentation/`, or updating `ISSUE_LOG.md` | `tracker-docs` |
| About to claim "ready for UAT"/release-ready, or running sprint 0007/0008 work | `uat-gate` |
| Editing `CLAUDE.md` or anything under `.claude/` | `guidance-change` |

Recurring-bug categories `IT-1`..`IT-6` and their checklists: `documentation/standards/ISSUE_LOG.md`.
