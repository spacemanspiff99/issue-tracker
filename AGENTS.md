# Codex Project Instructions

These instructions apply to the whole repository. They are for OpenAI Codex only. Keep Cursor guidance in `.cursor/rules/`; put Codex command approval policy only in `.codex/rules/*.rules`.

## Project Shape

- Issue Tracker is a FastAPI + Jinja + SQLAlchemy 2.x + Alembic + PostgreSQL application with a stdio MCP server backed by the same service layer.
- Keep implementation under `src/issue_tracker/`, with web, MCP, domain, services, and repositories separated.
- Keep Alembic migrations in the root `migrations/` folder. Do not add a second migration tree.
- Use the single `main` branch strategy unless the repository explicitly adopts another branch model. Prefer one behavior change per PR.

## Domain Rules

- Web routes and MCP tools must call the same service-layer operations for issue, sprint, dependency, category, and issue-log behavior.
- MCP tools should return compact summaries by default. Full issue text, acceptance criteria, and history should be opt-in by ID.
- Do not duplicate lifecycle logic in templates, routes, and MCP tools.

## Issues, Prompts, And STOP Handoffs

- Execution prompts live in `documentation/prompts/` or issue/sprint planning folders if the app starts dogfooding exported tracker plans.
- Prompts must include context, files in scope, acceptance criteria, verification commands, and a `## STOP` section naming what remains or the next prompt.
- Do not run a large implementation prompt in the same conversation that created it; use a fresh session for long handoffs.
- Split schema, service, web, MCP, and deployment changes unless a single invariant requires them together.

## Acceptance Criteria

- Every issue or prompt needs pass/fail acceptance criteria before implementation starts.
- If a change touches `documentation/standards/ISSUE_LOG.md` categories, inline the matching prevention checklist:
  - `IT-1`: tracker state integrity.
  - `IT-2`: category and AC binding.
  - `IT-3`: schema and migration safety.
  - `IT-4`: MCP contract and token discipline.
  - `IT-5`: auth and secret safety.
  - `IT-6`: deployment and configuration drift.
- Closing an issue should preserve immutable close metadata, verification evidence, and PR or commit references when available.

## Verification

- Service behavior should have tests before the same behavior is treated as complete through web routes or MCP tools.
- Schema changes require an Alembic migration plus a check that `alembic upgrade head` works on an empty database.
- Deployment is not verified until `/health` confirms database connectivity.
- If a command is blocked because the project is not initialized yet, report the exact command and verify the files that do exist.

## Model And Evidence

- Prefer GPT-5.5 for Codex work when available; use GPT-5.4 as fallback and GPT-5.4-mini for narrow subagent work.
- If the user explicitly asks for a model, use it when the environment supports it.
- Final reports should name changed files, verification commands, blocked checks, and any remaining STOP handoff.
