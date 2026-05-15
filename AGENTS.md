# Codex Project Instructions

These instructions apply to the whole repository. They are for OpenAI Codex only. Keep Cursor guidance in `.cursor/rules/`; put Codex command approval policy only in `.codex/rules/*.rules`.

## Project Shape

- Issue Tracker is a FastAPI + Jinja + SQLAlchemy 2.x + Alembic + PostgreSQL application with a stdio MCP server backed by the same service layer.
- Keep implementation under `src/issue_tracker/`, with web, MCP, domain, services, and repositories separated.
- Keep Alembic migrations in the root `migrations/` folder. Do not add a second migration tree.
- Keep docs in `documentation/`, deployment assets in `deployment/`, and root files limited to unavoidable project metadata.
- Do not create orphan documentation: every new doc must be linked from the relevant planning doc, guide index, README section, issue, sprint, or another discoverable document.
- Do not create orphan rules or guidance: every new rule file must be referenced from `AGENTS.md`, `.cursor/rules/core.mdc`, the mirror workflow, or the relevant harness entrypoint.
- Use the single `main` branch strategy unless the repository explicitly adopts another branch model. Prefer one behavior change per PR.

## Harness And Model Guidance

- Preserve harness boundaries: Cursor rules belong in `.cursor/rules/`, Codex project guidance belongs in `AGENTS.md`, Codex command approval policy belongs in `.codex/rules/*.rules`, and Claude Code memory belongs in `CLAUDE.md`.
- Do not copy Codex/GPT model guidance into Cursor `.mdc` files unless Cursor behavior is intentionally changing too.
- Prefer GPT-5.5 for Codex work when available; use GPT-5.4 as fallback and GPT-5.4-mini only for narrow, low-risk coding or delegated subagent work.
- Use GPT-5.5 `medium` for normal implementation, tests, documentation, and focused route/service changes.
- Use GPT-5.5 `high` for architecture, schema or migration invariants, auth and secrets, deployment, MCP contracts, manual UAT release decisions, difficult debugging, and any work that can corrupt tracker state.
- Each issue, sprint task, or execution prompt must name the recommended model and reasoning level before implementation starts. If the active model/reasoning does not match, record the mismatch and either adjust or explicitly accept the risk.
- When delegating to subagents, use GPT-5.5 with `high` reasoning when the subtask is complex, security-sensitive, schema-critical, deployment-critical, MCP-contract-sensitive, or likely to require difficult debugging. Use lighter models only for bounded mechanical subtasks with low blast radius.
- Follow OpenAI Codex guidance: outcome-first instructions, explicit success criteria, allowed side effects, verification expectations, evidence rules, and clear stop conditions.
- For planning or prompt creation, use sequential role passes as relevant: project manager for scope, engineering manager for decomposition, backend/frontend engineer for implementation risk, DevOps for runtime and migration risk, and QA engineer for verification. Do not use these as parallel personas unless the user explicitly requests parallel agent work.

## Domain Rules

- Web routes and MCP tools must call the same service-layer operations for issue, sprint, dependency, category, and issue-log behavior.
- MCP tools should return compact summaries by default. Full issue text, acceptance criteria, and history should be opt-in by ID.
- Do not duplicate lifecycle logic in templates, routes, and MCP tools.
- Treat categories as project-scoped data. Do not hardcode peer project taxonomies from weather-app, investments, storyteller, or any other project.
- Preserve the manual tracker ID convention: issues and sprints share one project-local `NNNN` sequence, displayed with four zero-padded digits.

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
- Debug from evidence first. Inspect logs, runtime output, request/response bodies, and database state before changing logic. If the evidence is missing, add the smallest useful logging or diagnostic check.
- UI-facing changes require browser or route-level verification that proves the page is styled and usable; a clean server log or lack of JavaScript errors is not enough.
- Local manual UAT readiness requires a fresh container build, explicit migration, pytest gate, `/health` database check, setup/login path, project/issue/dependency/sprint/close path, and a written pass/fail notes location.
- If a command is blocked because the project is not initialized yet, report the exact command and verify the files that do exist.
- After code or guidance changes, run the smallest relevant validation command and report anything blocked.

## Safety Boundaries

- Do not commit secrets, `.env` files, local credentials, database dumps, backups, generated exports, or large local artifacts.
- Do not install missing system packages, CLIs, package-manager dependencies, or host tools from Codex. If a required tool is missing, stop and ask the user to install or authenticate it manually, then continue after they confirm it is ready.
- Do not run destructive commands such as `rm -rf`, `git reset --hard`, or force-push operations unless the user explicitly asks and confirms.
- This repository is the authoritative source for issue-tracker guidance. `spacemanspiff99/vibecoding` receives mirrored guidance only.
- Do not edit mirrored guidance in `spacemanspiff99/vibecoding` by hand. Edit this source repository, then let the mirror workflow publish to vibecoding.

## Evidence And Closeout

- Final reports should name changed files, verification commands, blocked checks, and any remaining STOP handoff.
- Do not claim a workflow works until it has been tested through the relevant surface: service tests, route tests, MCP tests, or Docker smoke tests.
