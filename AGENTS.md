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

## Dual Tracker Dogfooding

- During dogfooding, use both systems: local markdown planning under `documentation/` and the running Issue Tracker project for this repository.
- Markdown remains the durable, reviewable Git source for rules, sprint plans, issue prompts, UAT notes, and handoffs until a deliberate migration/export workflow replaces it.
- The issue-tracker database is the active working backlog and sprint board for local development. Keep it aligned with markdown when creating, starting, closing, or reprioritizing work.
- Before implementation starts, verify the relevant tracker issue or sprint exists and has pass/fail acceptance criteria, recommended model/reasoning, verification commands, and STOP handoff. If it only exists in markdown, add or update the tracker record; if it only exists in the tracker, add or link a discoverable markdown note when long-lived guidance or handoff context is needed.
- Before backlog or sprint planning, query the active tracker project for voice/audio intake issues, especially titles or metadata containing `To process`, `voice-feedback`, `audio`, `intake`, or `clarify`. Include those items in the plan or explicitly record why they are deferred.
- After implementation, update both surfaces as appropriate: tracker status/close metadata/evidence for work state, and markdown docs for durable guidance, rules, UAT notes, or prompts.
- Do not treat local database state as the only record of project decisions. For risky work, export or otherwise record enough evidence to recover the tracker state before destructive local reset.
- Keep generated tracker exports out of git unless a future issue explicitly adopts a reviewed export artifact format and location.

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

## UI Provenance

- If a UI, template, component, screenshot-derived layout, or styling direction is identified as coming from MagicPatterns, treat it as protected source design.
- Do not rewrite, restyle, simplify, replace, or substantially modify MagicPatterns UI without explicit user instruction naming that change.
- When implementing behavior around a MagicPatterns UI, preserve its layout, spacing, visual hierarchy, labels, and component structure unless the requested functionality cannot work without a targeted adjustment.
- If a targeted adjustment is required, keep it minimal, document the divergence in the relevant issue/sprint or guide, and verify the rendered UI.

## Issues, Prompts, And STOP Handoffs

- Execution prompts live in `documentation/prompts/` or issue/sprint planning folders if the app starts dogfooding exported tracker plans.
- Prompts must include context, files in scope, acceptance criteria, verification commands, and a `## STOP` section naming what remains or the next prompt.
- Do not run a large implementation prompt in the same conversation that created it; use a fresh session for long handoffs.
- Split schema, service, web, MCP, and deployment changes unless a single invariant requires them together.
- When the user asks to execute or finish a large scoped sprint, do not reinterpret it as permission to complete only a slice. First query the tracker sprint and durable markdown plan, enumerate every remaining issue, then build a phased execution plan that is explicitly designed to close the full sprint.
- Large scoped sprint plans must sequence all remaining issues, name dependency-aware phases, and say where subagents should be used sequentially or in parallel with disjoint write scopes. If the sprint is too large for one response, continue iterating until it is complete or genuinely blocked.
- A large sprint STOP handoff may not say merely that the next slice is ready. It must say one of: the sprint is complete and closed; the sprint is blocked by a specific owner action; or the user explicitly accepted named deferrals for remaining issues.
- For oversized dogfood sprints, close completed tracker issues as they pass verification, keep the sprint active until every assigned issue is done or explicitly deferred by the user, and keep the markdown sprint plan updated with the remaining issue list and final gate evidence.

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
- When the user asks to deploy to UAT, first treat the current dev checkout as the intended source of truth. Check `git status`, identify uncommitted product/deployment/doc changes, and do not dispatch the GitHub Actions UAT workflow until the intended changes are committed and pushed to the branch/ref being deployed, or the user explicitly says to deploy a named older ref despite local drift.
- Before dispatching a UAT workflow, state the exact branch and commit SHA that will deploy and pass that SHA as `expected_deploy_sha`. If the local checkout has uncommitted changes or the local branch differs from the remote ref, stop and resolve that mismatch instead of assuming GitHub has the same state.
- UAT and production deployment move code only and must preserve the existing target database by default. Do not reset target volumes, drop/recreate target databases, replace UAT data with dev data, or alter production data except through reviewed forward migrations.
- Production data is the durable source of truth. Production deploys require pre-migration backup, forward-only migrations, health checks, and a clear deployed SHA; they must never include implicit data copy, reset, truncate, downgrade, or restore behavior.
- Copying production data down to UAT or dev for realistic testing is a separate data refresh operation, not a deploy. It must be explicit about source `prod`, target `uat` or `dev`, destructive overwrite of the target database, pre-refresh backups of both source and target metadata, secret/session sanitization expectations, and post-restore verification. Never copy UAT or dev data upward into production.
- If the app has no production data yet and the user explicitly chooses UAT as the staging environment, a dev-to-UAT representative seed refresh may stand in for production-like staging. Treat it as a destructive data refresh, not a normal deploy: create a tracker sprint/issue plan first, confirm source `dev` and target `uat`, take and verify both the dev seed dump and UAT pre-refresh backup, overwrite only UAT, run migrations and representative data checks on UAT, and record pass/fail evidence before any production-readiness claim.
- A sprint, prompt, checklist, or previous plan may describe destructive work, but it is never itself permission to execute destructive commands. Before overwriting any target database, stop and ask exactly: `STOP: I am about to overwrite <target> from <source>. Reply CONFIRM OVERWRITE <target> to proceed.` Do not proceed unless the latest user response contains that exact target-specific confirmation.
- If execution stops for SSH, credentials, missing tooling, auth, network access, or another blocker, resolving that blocker only authorizes retrying the blocked non-destructive check. It does not authorize later destructive steps, UAT/prod deploys, database restores, volume resets, or workflow dispatches.
- Before any UAT or production mutation, state the exact operation, source, target, branch/SHA for code deploys, whether data will be overwritten, backup plan or existing backup path, rollback outline, and then stop for explicit confirmation when the operation mutates remote code or data.
- Debug from evidence first. Inspect logs, runtime output, request/response bodies, and database state before changing logic. If the evidence is missing, add the smallest useful logging or diagnostic check.
- UI-facing changes require browser or route-level verification that proves the page is styled and usable; a clean server log or lack of JavaScript errors is not enough.
- Local manual UAT readiness requires a fresh container build, explicit migration, pytest gate, `/health` database check, setup/login path, project/issue/dependency/sprint/close path, and a written pass/fail notes location.
- Run Playwright and browser UAT from the Docker image or an existing app container. Browser runtime dependencies such as Chromium libraries belong in the container image, for example through the Dockerfile's Playwright install step; do not install Playwright system dependencies on the host from Codex.
- Before Docker preflight builds, check available disk space with `df -h / /tmp` and `docker system df`. After isolated preflight builds or failed build attempts, remove the temporary preflight image and unused build cache when needed so large Playwright/browser layers do not fill the dev host. Prefer targeted cleanup such as `docker image rm <preflight-image>` and `docker builder prune`; ask before broad `docker system prune`, and never remove named volumes that may contain tracker data unless the user explicitly confirms that target.
- If a command is blocked because the project is not initialized yet, report the exact command and verify the files that do exist.
- After code or guidance changes, run the smallest relevant validation command and report anything blocked.

## Safety Boundaries

- Do not commit secrets, `.env` files, local credentials, database dumps, backups, generated exports, or large local artifacts.
- Do not install missing system packages, CLIs, package-manager dependencies, or host tools from Codex. If a required tool is missing, stop and ask the user to install or authenticate it manually, then continue after they confirm it is ready.
- Do not run host-level Playwright installers such as `playwright install --with-deps` outside Docker. If browser dependencies are missing, rebuild the container image or run the browser test inside the app container.
- Do not run destructive commands such as `rm -rf`, `git reset --hard`, or force-push operations unless the user explicitly asks and confirms.
- When running Docker Compose preflight checks from a temporary worktree on the dev host, use a unique compose project name or otherwise prove it will not recreate, stop, or replace the live dev app containers. Do not disrupt the user's active dev URL as part of UAT preparation.
- Treat Docker image/cache cleanup as an operational safety step, not a substitute for verification. Removing temporary images and build cache is acceptable after evidence is captured; removing containers, volumes, databases, or broad Docker resources requires the same target-specific care as other destructive operations.
- Treat production-to-UAT/dev and dev-to-UAT data refresh as destructive to the target environment. Require the exact `CONFIRM OVERWRITE <target>` confirmation before overwriting target data, even when the operation is intentionally non-destructive to production.
- Generic approval such as `ok`, `continue`, `ssh key setup`, `credentials ready`, `try again`, or approval of command access is not destructive-action approval.
- This repository is the authoritative source for issue-tracker guidance. `spacemanspiff99/vibecoding` receives mirrored guidance only.
- Do not edit mirrored guidance in `spacemanspiff99/vibecoding` by hand. Edit this source repository, then let the mirror workflow publish to vibecoding.

## Evidence And Closeout

- Final reports should name changed files, verification commands, blocked checks, and any remaining STOP handoff.
- Do not claim a workflow works until it has been tested through the relevant surface: service tests, route tests, MCP tests, or Docker smoke tests.
