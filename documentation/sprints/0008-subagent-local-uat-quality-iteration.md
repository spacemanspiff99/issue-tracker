# Sprint 0008: Subagent Local UAT Quality Iteration

Status: planned
Recommended parent model: GPT-5.5 high
Purpose: iterate with focused subagents until the MVP is high enough quality and functional enough for local manual UAT.

## Goal

Turn the current MVP implementation into a locally testable manual UAT candidate by running evidence-driven subagent loops across runtime, backend correctness, web usability, MCP parity, docs, and release closeout.

This sprint does not add non-MVP product scope. It exists to harden the existing MVP path:

- setup and login
- project and category management
- issue creation with required acceptance criteria
- dependency add and cycle rejection
- sprint creation and issue assignment
- issue close with immutable originating LLM metadata
- issue-log visibility
- import/export smoke
- compact MCP tools
- local Docker/Compose runtime

## Rules To Load

- `.cursor/rules/core.mdc`
- `.cursor/rules/agents.mdc`
- `.cursor/rules/ac.mdc`
- `.cursor/rules/backend.mdc`
- `.cursor/rules/devops.mdc`
- `AGENTS.md`
- `documentation/planning/EXTERNAL_RULE_REVIEW.md`
- `documentation/sprints/0007-local-manual-uat-readiness.md`

## Sprint Operating Rules

- Parent coordinator uses GPT-5.5 high.
- Routine doc or narrow test workers may use GPT-5.5 medium.
- Runtime, schema, auth, MCP, release, and difficult debugging workers use GPT-5.5 high.
- Every subagent gets one ownership scope and one binary exit condition.
- Subagents are sequential when outputs depend on each other; only independent read-only reviews or disjoint file edits run in parallel.
- Workers must not revert unrelated edits. They must adapt to current workspace state.
- Workers must report changed files, verification commands, pass/fail result, blockers, and the next smallest retry step.
- A failed gate starts another focused worker iteration rather than broad refactoring.

## Sequential Role Review

Project manager: Keep scope limited to local manual UAT readiness. Defer production deployment, GitHub sync, multi-user roles, drag/drop planning, and full markdown migration.

Engineering manager: Split work by ownership so workers do not collide. Runtime gate comes first because later browser and MCP checks need a working stack.

Backend engineer: Protect service invariants: shared sequence allocation, required AC, dependency cycle rejection, category scoping, and immutable close metadata.

Frontend engineer: Verify pages are styled and usable in a browser. Route tests alone are not enough for UAT readiness.

DevOps engineer: Keep migrations explicit, Docker commands container-only, reset instructions local-only, and no host dependency pollution.

QA engineer: Convert every local UAT path into pass/fail evidence with blocker notes and follow-up issue mapping.

## Subagent Backlog

### Worker 01: Docker Runtime Gate

Recommended model: GPT-5.5 high
Ownership: `deployment/`, `README.md`, `documentation/guides/local-development.md`, runtime command evidence only.

Tasks:

- Confirm Docker daemon access for the current user.
- Build the app image.
- Start local PostgreSQL through Compose.
- Run explicit Alembic migration.
- Run pytest through the app service.
- Start the stack and verify `/health`.

Validation:

```bash
docker compose -f deployment/docker-compose.local.yml config
docker compose -f deployment/docker-compose.local.yml build
docker compose -f deployment/docker-compose.local.yml run --rm app alembic upgrade head
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/
docker compose -f deployment/docker-compose.local.yml up
```

Exit condition: local stack reaches `/health` with database connectivity, or Docker access remains the only recorded blocker with exact remediation.

### Worker 02: Backend Invariant Audit

Recommended model: GPT-5.5 high
Ownership: `src/issue_tracker/domain/`, `src/issue_tracker/repositories/`, `src/issue_tracker/services/`, `tests/unit/`, `tests/integration/`.

Tasks:

- Review sequence allocation, issue status transitions, close metadata, category scoping, and dependency cycle handling.
- Add or repair tests for any missing invariant.
- Confirm repository boundaries are respected.
- Confirm migration and model constraints agree.

Validation:

```bash
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/unit tests/integration
docker compose -f deployment/docker-compose.local.yml run --rm app alembic upgrade head
```

Exit condition: backend invariants pass through tests and migration gate.

### Worker 03: Web Manual UAT Path

Recommended model: GPT-5.5 high
Ownership: `src/issue_tracker/web/`, `tests/integration/test_web_routes.py`, `documentation/guides/manual-uat.md`.

Tasks:

- Verify setup, login, project, category, issue validation, dependency, sprint, assignment, close, and issue-log pages.
- Ensure validation errors preserve user context.
- Ensure pages are styled and usable, not raw unstyled HTML.
- Add route tests for any missing pass/fail behavior.
- Write the browser UAT script if it does not exist.

Validation:

```bash
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/integration/test_web_routes.py
docker compose -f deployment/docker-compose.local.yml up
```

Manual validation: browser walkthrough recorded in UAT notes.

Current status: guide scaffold created in `documentation/guides/manual-uat.md`; runtime execution remains blocked in the active Codex process until Docker group membership is inherited by a fresh session.

Exit condition: a human can complete the full web UAT path locally with expected results and notes.

### Worker 04: MCP Parity And Token Discipline

Recommended model: GPT-5.5 high
Ownership: `src/issue_tracker/mcp/`, `tests/integration/test_mcp_tools.py`, `documentation/guides/mcp.md`.

Tasks:

- Verify implemented MCP tools match the documented MVP list.
- Confirm MCP tools call the same services as web routes.
- Confirm list/search output is bounded and compact.
- Confirm full acceptance criteria are opt-in by ID.
- Confirm stderr/stdout behavior does not pollute stdio protocol.

Validation:

```bash
docker compose -f deployment/docker-compose.local.yml run --rm app python -m issue_tracker.mcp.server --smoke
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/integration/test_mcp_tools.py
```

Exit condition: MCP smoke and compact-output tests pass.

### Worker 05: Import Export And Reset Safety

Recommended model: GPT-5.5 high
Ownership: `src/issue_tracker/cli.py`, `tests/integration/test_cli_import_export.py`, `documentation/guides/backup-restore.md`, optional `documentation/guides/manual-uat.md`.

Tasks:

- Verify export excludes secrets, sessions, password hashes, logs, dumps, and environment values.
- Verify import requires explicit category mapping when source categories exist.
- Document local-only reset commands.
- Ensure generated exports and backups remain gitignored.

Validation:

```bash
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/integration/test_cli_import_export.py
git status --short --ignored
```

Exit condition: import/export and local reset instructions are safe enough for manual UAT.

### Worker 06: UAT Findings And Release Closeout

Recommended model: GPT-5.5 high
Ownership: `documentation/uat/`, `documentation/sprints/0007-local-manual-uat-readiness.md`, `documentation/sprints/0008-subagent-local-uat-quality-iteration.md`.

Tasks:

- Create UAT notes template.
- Record environment, commit SHA, browser, commands, tester, date, pass/fail, blockers, and screenshots or notes path.
- Triage any failure into must-fix-before-UAT, can-fix-after-UAT, or non-MVP backlog.
- State the final local manual UAT decision.

Validation:

```bash
git status --short --branch
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/
```

Current status: UAT notes template created in `documentation/uat/TEMPLATE-local-uat.md`.

Exit condition: the sprint closeout says one of `ready`, `ready with caveats`, or `not ready`, with evidence.

## Definition Of Ready For Manual UAT

- Docker daemon access is fixed for the current user without setting `/var/run/docker.sock` world-writable.
- Compose config validates.
- App image builds from a fresh build.
- Alembic migration runs explicitly.
- Pytest suite passes in the app container.
- Local stack starts and `/health` reports database connectivity.
- Browser UAT path is documented and complete.
- MCP smoke passes and compact-output tests pass.
- Import/export smoke passes.
- UAT notes template exists and has an initial run record.
- No secrets, `.env`, database dumps, backups, generated exports, logs, or large artifacts are committed.

## Validation Gate

Run this final gate before closing Sprint 0008:

```bash
docker compose -f deployment/docker-compose.local.yml config
docker compose -f deployment/docker-compose.local.yml build
docker compose -f deployment/docker-compose.local.yml run --rm app alembic upgrade head
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/
docker compose -f deployment/docker-compose.local.yml run --rm app python -m issue_tracker.mcp.server --smoke
git diff --check
LC_ALL=C grep -RIn '[^ -~]' README.md AGENTS.md .cursor/rules .github/workflows documentation src tests migrations deployment .env.example pyproject.toml alembic.ini
```

### Evidence 2026-05-15

Branch: `main`
Base commit: `198a534`

| Check | Result | Evidence |
|---|---|---|
| Docker access | Pass | `id` showed user `akun` in groups `akun,nogroup`; `/var/run/docker.sock` was `nobody:nogroup` with group read/write. |
| Compose config | Pass | `docker compose -f deployment/docker-compose.local.yml config` rendered valid services, network, and volume configuration. |
| Build | Pass | `docker compose -f deployment/docker-compose.local.yml build` completed after adding the missing `itsdangerous` runtime dependency. |
| Migration | Pass | `docker compose -f deployment/docker-compose.local.yml run --rm app alembic upgrade head` completed against local PostgreSQL. |
| Tests | Pass | `docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/` reported `15 passed`; pytest emitted a non-blocking cache permission warning for `/app/.pytest_cache`. |
| MCP smoke | Pass | `docker compose -f deployment/docker-compose.local.yml run --rm app python -m issue_tracker.mcp.server --smoke` returned `{"ok": true}` with the expected tool list. |
| Health | Pass | `curl -fsS http://localhost:8000/health` returned `{"ok":true,"database":"ok"}` with the Compose stack running. |
| Diff whitespace | Pass | `git diff --check` produced no output. |

## STOP

Stop only after the coordinator records one of these outcomes:

- Local manual UAT ready.
- Local manual UAT ready with named caveats and owner-accepted risks.
- Local manual UAT not ready, with exact blockers, owner actions, and the next worker to run.

Do not expand this sprint into production deployment, GitHub sync, multi-user roles, drag/drop planning, or full markdown migration.
