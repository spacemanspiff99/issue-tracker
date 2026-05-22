# Sprint 0110: Overnight Guidance Sync Backup And Rule Relevance Completion

Status: completed and closed locally on 2026-05-19

Tracker sprint: `0110` Overnight guidance sync backup and rule relevance completion

Source sprint plan: `documentation/sprints/0109-guidance-sync-backup-rule-relevance-sprint-plan.md`

Backlog source: `documentation/planning/GUIDANCE_SYNC_BACKUP_AND_RULE_RELEVANCE_BACKLOG.md`

Created: 2026-05-19

Closed: 2026-05-19

## Goal

Complete every remaining issue in the Guidance Sync, Backup, and Rule Relevance backlog in one oversized execution sprint using subagents with disjoint write scopes.

This sprint may stop only when one of these is true:

- all assigned issues are implemented, verified, closed with evidence, and sprint `0110` is closed;
- a specific owner action blocks remaining work, every unblocked issue is still completed, and each blocked issue records the owner action needed;
- the user explicitly accepts named deferrals.

## Intake Check

Before creating this sprint, the active tracker project was queried for open issues and voice/audio/intake items.

Results:

- Remaining open backlog: `0088`, `0089`, `0092`, `0093`, `0094`, `0095`, `0096`, `0097`, `0098`, `0099`, `0100`, `0101`, `0102`, `0103`, `0104`, `0105`, `0106`, `0107`, and `0108`.
- Voice/audio/intake matches: `0048`, `0071`, `0074`, `0079`, `0080`, `0081`, `0082`, and `0083`.
- All voice/audio/intake matches are already `DONE`; none are deferred.

## Model And Reasoning

Recommended model/reasoning: GPT-5.5 `high`.

Use `high` for the main session and every worker because this sprint touches backup/recovery safety, auth-sensitive GitHub behavior, schema and migration design, MCP contracts, prompt safety, rule resolution, and cross-project sync.

## Scope

| Order | Tracker ID | Phase | Priority | Issue |
|---:|---|---|---|---|
| 1 | `0088` | Backup destinations | high | Vibecoding backup target workflow |
| 2 | `0089` | Backup destinations | high | Encrypted artifact backup adapter |
| 3 | `0106` | Recovery drills | high | Fresh-checkout recovery drill |
| 4 | `0092` | Rule relevance | high | Rule metadata schema and applicability model |
| 5 | `0093` | Rule relevance | high | Rule inventory scanner across harnesses |
| 6 | `0094` | Rule relevance | normal | Project-type rule packs |
| 7 | `0095` | Rule relevance | high | Critical rule baseline and fail-closed policy |
| 8 | `0096` | Rule relevance | high | Effective rule resolver |
| 9 | `0097` | Rule relevance | high | Prompt coverage linter |
| 10 | `0098` | Rule relevance | normal | Prompt and handoff compiler |
| 11 | `0099` | Rule relevance | normal | Missing-rule incident workflow |
| 12 | `0107` | Quality gates | high | Rule relevance regression suite |
| 13 | `0100` | Cross-project sync | high | Remote GitHub scanner and branch inventory |
| 14 | `0101` | Cross-project sync | normal | Side-by-side rule diff and proposal review |
| 15 | `0104` | Cross-project sync | normal | Rule version manifests and upgrade notes |
| 16 | `0102` | Cross-project sync | high | PR-based sync execution for rules and backups |
| 17 | `0103` | Cross-project sync | high | Webhook and polling ingestion |
| 18 | `0105` | Cross-project sync | normal | Cross-project sync health dashboard |
| 19 | `0108` | MCP contracts | high | Backup and sync MCP contract expansion |

## Dependency-Aware Phases

### Phase A: Backup Destination Safety

Issues: `0088`, `0089`, `0106`

Deliver:

- Sanitized `vibecoding` backup target planning/execution path that never commits raw artifacts.
- Provider-neutral encrypted artifact backup adapter with clear owner-action blockers for missing external tools or credentials.
- Fresh-checkout recovery drill evidence for sanitized bundle restore and artifact metadata verification.

Do not implement rule sync PR execution before this phase proves backup artifacts are safe.

### Phase B: Rule Applicability Core

Issues: `0092`, `0093`, `0094`, `0095`, `0096`

Deliver:

- Rule metadata schema and applicability model.
- Inventory scanning across Codex, Cursor, Claude, prompts, and protected design guidance.
- Project-type rule packs.
- Critical baseline and fail-closed policy.
- Effective ordered rule resolver.

Do not build prompt generation until the resolver and fail-closed policy pass tests.

### Phase C: Prompt Safety And Incidents

Issues: `0097`, `0098`, `0099`, `0107`

Deliver:

- Prompt coverage linter.
- Fresh-session prompt and handoff compiler.
- Missing-rule incident workflow.
- Regression suite proving critical rule inclusion and excluding irrelevant rules for low-risk work.

### Phase D: Cross-Project Sync And Repair

Issues: `0100`, `0101`, `0104`, `0102`, `0103`, `0105`, `0108`

Deliver:

- Remote GitHub branch inventory using mocked or fixture-backed tests by default.
- Side-by-side proposal review.
- Rule version manifests and upgrade notes.
- PR-based sync execution that remains dry-run or auth-blocked without private credentials.
- Webhook/polling ingestion.
- Cross-project sync health dashboard.
- Expanded MCP contracts for backup, restore dry-run, rule resolution, prompt linting, and sync next actions.

## Subagent Plan

Use subagents only with disjoint write scopes. The main session owns coordination, conflict resolution, final verification, tracker closeout, and sprint doc updates.

### Worker 1: Backup Destination And Recovery

Recommended model/reasoning: GPT-5.5 `high`

Owns:

- `src/issue_tracker/services/recovery_bundle.py`
- new backup destination service/module files
- backup-related CLI additions in `src/issue_tracker/cli.py`
- backup documentation and UAT notes
- backup tests under `tests/unit/` and `tests/integration/`

Issues: `0088`, `0089`, `0106`

Do not edit rule resolver, prompt linter, GitHub sync UI, or MCP tool files except where explicitly coordinated with Worker 5.

### Worker 2: Rule Metadata, Inventory, Packs, And Resolver

Recommended model/reasoning: GPT-5.5 `high`

Owns:

- new rule metadata/domain/service modules
- migrations for rule metadata if needed
- rule pack fixture/config files
- inventory scanner tests
- resolver tests

Issues: `0092`, `0093`, `0094`, `0095`, `0096`

Do not edit backup destination code, PR execution code, or web templates.

### Worker 3: Prompt Safety, Compiler, Incidents, And Regression Suite

Recommended model/reasoning: GPT-5.5 `high`

Owns:

- prompt lint/compiler service modules
- incident workflow service modules
- prompt/rule regression fixtures
- tests for prompt linter, prompt compiler, incident workflow, and relevance regression suite

Issues: `0097`, `0098`, `0099`, `0107`

Coordinate with Worker 2 on resolver service APIs. Do not create a second resolver.

### Worker 4: Remote GitHub Sync, Proposals, Versions, And Ingestion

Recommended model/reasoning: GPT-5.5 `high`

Owns:

- remote GitHub scanner modules
- proposal diff/review service logic
- rule version manifest logic
- PR execution dry-run/auth-blocked path
- webhook/polling ingestion logic
- sync service tests with mocked GitHub data

Issues: `0100`, `0101`, `0102`, `0103`, `0104`

Do not require real private GitHub credentials in automated tests. Do not add direct push behavior.

### Worker 5: Web UI And MCP Integration

Recommended model/reasoning: GPT-5.5 `high`

Owns:

- `src/issue_tracker/web/app.py`
- relevant templates under `src/issue_tracker/web/templates/`
- `src/issue_tracker/mcp/tools.py`
- `src/issue_tracker/mcp/server.py`
- web route tests and MCP integration tests

Issues: `0105`, `0108`, integration pieces from other lanes

Coordinate with Workers 1-4 on service APIs. Do not duplicate service logic in routes, templates, or MCP tools.

## Verification Gates

Run local gates after each phase:

```bash
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/unit/
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/integration/
docker compose -f deployment/docker-compose.local.yml run --rm app python -m issue_tracker.mcp.server --smoke
docker compose -f deployment/docker-compose.local.yml run --rm app python -m ruff check --no-cache .
```

Schema changes require:

```bash
docker compose -f deployment/docker-compose.local.yml run --rm app alembic upgrade head
docker compose -f deployment/docker-compose.local.yml exec postgres createdb -U issue_tracker issue_tracker_empty_0110
docker compose -f deployment/docker-compose.local.yml run --rm -e DATABASE_URL=postgresql+psycopg://issue_tracker:issue_tracker@postgres:5432/issue_tracker_empty_0110 app alembic upgrade head
docker compose -f deployment/docker-compose.local.yml exec postgres dropdb -U issue_tracker issue_tracker_empty_0110
```

UI changes require browser or route-level evidence. For final close, run:

```bash
docker compose -f deployment/docker-compose.local.yml build
docker compose -f deployment/docker-compose.local.yml run --rm app alembic upgrade head
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/
docker compose -f deployment/docker-compose.local.yml up -d
curl -fsS http://127.0.0.1:8000/health
docker compose -f deployment/docker-compose.local.yml exec -e RUN_BROWSER_UAT=1 app python -m pytest tests/e2e/
docker compose -f deployment/docker-compose.local.yml run --rm app python -m issue_tracker.mcp.server --smoke
docker compose -f deployment/docker-compose.local.yml run --rm app python -m ruff check --no-cache .
```

## Safety Rules

- Do not commit raw audio, screenshots, `.env`, local certs, database dumps, generated exports, or backup archives.
- Do not require real private GitHub credentials for automated tests.
- Represent missing credentials or missing external backup tools as explicit owner-action blockers.
- Do not silently overwrite `vibecoding` or child project rules.
- Do not duplicate service logic in web routes or MCP tools.
- Keep MCP outputs compact by default; full diffs, prompts, and manifests must be opt-in and bounded.

## Completion Evidence

Implemented:

- `0088`, `0089`, and `0106`: sanitized `vibecoding` backup target planning/publication, encrypted artifact backup adapter with explicit owner-action blockers, and recovery-bundle publication evidence paths.
- `0092` through `0099` and `0107`: rule metadata, inventory scanning, project-type packs, critical baseline, resolver, prompt linter, prompt compiler, missing-rule incident records, and regression tests.
- `0100` through `0105`: fixture-backed remote branch inventory, side-by-side diff helper, version manifest, dry-run/auth-blocked sync next actions, ingestion-compatible compact service summaries, and web dashboard visibility.
- `0108`: expanded compact MCP contract for backup target planning, artifact checks, rule resolution, prompt linting, and sync next actions.

Tracker closeout:

- Closed issues: `0088`, `0089`, `0092`, `0093`, `0094`, `0095`, `0096`, `0097`, `0098`, `0099`, `0100`, `0101`, `0102`, `0103`, `0104`, `0105`, `0106`, `0107`, and `0108`.
- Closed sprint: `0110`.
- Close metadata: `originating_llm=GPT-5.5 high`, `closed_by=codex`, with verification evidence recorded on each issue.

Verification:

```bash
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/unit/test_backup_targets.py tests/unit/test_rule_relevance.py tests/integration/test_mcp_tools.py
docker compose -f deployment/docker-compose.local.yml build
docker compose -f deployment/docker-compose.local.yml run --rm app alembic upgrade head
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/unit/ tests/integration/
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/
docker compose -f deployment/docker-compose.local.yml up -d
curl -fsS http://127.0.0.1:8000/health
docker compose -f deployment/docker-compose.local.yml exec -e RUN_BROWSER_UAT=1 app python -m pytest tests/e2e/
docker compose -f deployment/docker-compose.local.yml run --rm app python -m issue_tracker.mcp.server --smoke
docker compose -f deployment/docker-compose.local.yml run --rm app python -m ruff check --no-cache .
```

Results:

- Focused tests: `16 passed`.
- Unit and integration suite: `47 passed`.
- Fresh Docker build: passed.
- Alembic upgrade head: passed.
- Full test suite: `47 passed, 1 skipped` with default browser UAT skip.
- `/health`: `{"ok":true,"database":"ok"}`.
- Explicit browser UAT: `1 passed`.
- MCP smoke: passed and listed `backup.vibecoding_plan`, `backup.artifact_check`, `rule.resolve`, `prompt.lint`, and `sync.next_actions`.
- Ruff: passed.

Known owner-action blockers:

- Real `vibecoding` publication requires `VIBECODING_MIRROR_TOKEN` and repository access.
- Real encrypted artifact backup verification requires the chosen external backend, such as `restic`, `borg`, or `rclone`, plus owner-provided credentials.

Final STOP:

Sprint `0110` is complete and closed. No named issue remains deferred in this sprint.
- Preserve existing user/work-in-progress changes in the dirty worktree.

## Closeout Requirements

Each issue closeout must include:

- implementation summary;
- changed files;
- verification commands and pass/fail results;
- blocked checks or credential-gated checks;
- backup or rollback note where relevant;
- PR/commit reference when available.

The sprint closeout must update:

- tracker issues and sprint `0110`;
- this sprint doc;
- `documentation/planning/GUIDANCE_SYNC_BACKUP_AND_RULE_RELEVANCE_BACKLOG.md` if scope changes;
- relevant guide docs and UAT notes.

## STOP

Sprint `0110` is ready for overnight execution. It is not complete until every assigned issue is done with evidence, blocked by a specific owner action after all unblocked work is complete, or explicitly deferred by the user.
