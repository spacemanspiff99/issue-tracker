# Comprehensive Test Plan

Date: 2026-05-21

Execution sprint: `documentation/sprints/0119-production-readiness-comprehensive-test-drill.md`

## Purpose

This plan defines how to test Issue Tracker backup, restore, Guidance Sync, rule relevance, MCP, migration, import/export, and deployment behavior without risking production tracker data.

The default rule is simple: do not test new mutating behavior against a production project first. Start with disposable data, then use a restored production-like database in staging, then UAT with verified backups, and only then production.

## Data Safety Principles

- Never point `DATABASE_URL` at production while testing new backup, restore, import, migration, Guidance Sync, or MCP behavior.
- Never run downgrade, reset, truncate, drop, recreate, or local Docker volume reset commands against external or production PostgreSQL.
- Always take a PostgreSQL backup before migrations on UAT or production-like hosts.
- Stop the deployment if the pre-migration backup cannot be created, copied, and verified as non-empty.
- Keep generated exports, backups, database dumps, raw audio, screenshots, local certificates, credentials, and `.env` files out of Git.
- Treat missing credentials or missing external backup tools as explicit owner-action blockers, not successful backup or sync states.
- Use review-first behavior for any repository mutation. Guidance Sync and backup publication should dry-run, block, or open reviewable PR-style changes before touching real repositories.

## Recommended Environments

1. **Unit and service tests**
   - SQLite in-memory or temporary test database.
   - No production data.
   - Used for service invariants, compact MCP contracts, drift classification, prompt linting, and backup adapters.

2. **Disposable local Docker PostgreSQL**
   - `deployment/docker-compose.local.yml`.
   - Fake projects only.
   - Safe for browser UAT, local import/export, local bundle export, and destructive local reset.
   - Browser UAT and Playwright dependency installation run inside the Docker image or app container, not on the host.

3. **Production-like staging database**
   - A separate PostgreSQL database restored from a production dump.
   - No production `DATABASE_URL`.
   - Realistic data shape, but tokens and outbound write credentials disabled.

4. **UAT host**
   - Production-like deployment path.
   - Requires pre-migration `pg_dump`.
   - Runs health, MCP smoke, browser UAT, and backup verification.

5. **Production**
   - Only after all earlier layers pass.
   - Forward-only migrations only.
   - Manual restore decisions only.

## Phase 1: Static, Unit, And Integration Gate

Run from the repository root:

```bash
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml config
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml build
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/unit/
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/integration/
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml run --rm app python -m issue_tracker.mcp.server --smoke
COMPOSE_PROJECT_NAME=issue_tracker_preflight POSTGRES_CONTAINER_NAME=issue-tracker-preflight-postgres APP_HTTP_PORT=18000 docker compose -f deployment/docker-compose.local.yml run --rm app python -m ruff check --no-cache .
```

On the dev host, check `http://192.168.10.20:8000/health` before and after these commands. The explicit Compose project, PostgreSQL container name, and host port keep temporary-worktree preflight from recreating the live dev stack.

Expected coverage:

- Service-layer issue, sprint, dependency, closeout, and validation invariants.
- Export/import behavior and category-mapping requirements.
- Recovery bundle creation, checksum validation, and dry-run restore.
- Backup target planning and owner-action blockers.
- Guidance Sync scan exclusion, drift classification, proposal approval, dry-run execution, event dedupe, and rollback planning.
- Rule inventory, effective rule resolution, prompt linting, prompt compilation, side-by-side diff summaries, and rule manifests.
- MCP compact output and service-backed mutating paths.

Exit criteria:

- All tests pass.
- MCP smoke lists expected tools.
- Ruff passes.
- No test requires private GitHub tokens, real `vibecoding` access, or real encrypted backup credentials.

## Phase 2: Migration Safety Gate

Run migrations against the disposable Docker database:

```bash
docker compose -f deployment/docker-compose.local.yml run --rm app alembic upgrade head
```

For schema-risk changes, also test an empty separate database:

```bash
docker compose -f deployment/docker-compose.local.yml exec postgres createdb -U issue_tracker issue_tracker_empty_test
docker compose -f deployment/docker-compose.local.yml run --rm -e DATABASE_URL=postgresql+psycopg://issue_tracker:issue_tracker@postgres:5432/issue_tracker_empty_test app alembic upgrade head
docker compose -f deployment/docker-compose.local.yml exec postgres dropdb -U issue_tracker issue_tracker_empty_test
```

For production-like confidence:

- Restore a production dump into a separate staging database.
- Disable outbound write credentials.
- Run `alembic upgrade head` against staging only.
- Verify row counts and representative project records before and after migration.
- Do not run downgrade, drop, truncate, reset, or recreate commands.

Exit criteria:

- Empty database migration succeeds.
- Restored production-like staging migration succeeds.
- Existing project, issue, sprint, guidance, and audit records remain present.
- No migration deletes tracker data as part of normal deploy.

## Phase 3: Disposable Local Browser UAT

Start the local stack:

```bash
docker compose -f deployment/docker-compose.local.yml up -d
curl -fsS http://localhost:8000/health
docker compose -f deployment/docker-compose.local.yml exec -e RUN_BROWSER_UAT=1 app python -m pytest tests/e2e/
```

Manual UAT should use a throwaway project such as `Manual UAT Project`.

Verify:

- First-run setup.
- Login and logout.
- Project creation.
- Category creation.
- Required acceptance criteria validation.
- Issue creation.
- Dependency creation and cycle rejection.
- Sprint creation and issue assignment.
- Issue close path and close metadata.
- Issue log view.
- Backlog, board, releases, intake, planning, backup, and Guidance Sync navigation.
- Desktop and mobile page usability.
- No secret values shown in the UI.

Local destructive reset is allowed only for the local Docker database:

```bash
docker compose -f deployment/docker-compose.local.yml down
docker volume rm deployment_issue_tracker_pgdata
```

Never adapt this reset flow to external or production PostgreSQL.

Exit criteria:

- `/health` returns `{"ok":true,"database":"ok"}`.
- Browser UAT passes.
- Manual path completes on disposable data.
- Generated screenshots, audio, exports, and backups remain ignored local artifacts.

## Phase 4: Backup And Recovery Bundle Gate

Create and validate a sanitized recovery bundle:

```bash
docker compose -f deployment/docker-compose.local.yml run --rm app issue-tracker export-recovery-bundle 1 exports/recovery-bundles/issue-tracker/latest
docker compose -f deployment/docker-compose.local.yml run --rm app issue-tracker restore-recovery-bundle exports/recovery-bundles/issue-tracker/latest --dry-run
```

Verify:

- `manifest.json` exists.
- Manifest checksums validate.
- Dry-run restore reports what would be created, skipped, merged, or rejected.
- Category mapping requirements are detected before mutation.
- Bundle includes tracker project records and Guidance Sync state.
- Bundle excludes password hashes, sessions, secrets, tokens, `.env`, raw audio, screenshots, local certificates, database dumps, generated caches, and raw artifact contents.

Important limitation:

- Current restore support is validation and dry-run oriented. Full mutating restore is not the primary recovery mechanism yet. Recovery confidence must also include PostgreSQL dump/restore drills.

Exit criteria:

- Bundle validation passes.
- Dry-run restore is `ok`.
- Secret and artifact exclusion checks pass.
- Recovery note records the exact bundle path and command output summary.

## Phase 5: Vibecoding Backup Target Gate

Test these cases without using the real `vibecoding` repository first:

- Missing `VIBECODING_MIRROR_TOKEN` returns blocked owner action.
- Invalid or corrupted bundle blocks publication.
- Fake local `vibecoding` checkout receives only sanitized files when dry-run is disabled in a controlled test.

Verify that no Git target receives:

- `.dump`
- `.sql`
- `.sqlite`
- `.db`
- `.webm`
- `.mp3`
- `.wav`
- `.png`
- `.jpg`
- `.jpeg`
- `.key`
- `.crt`
- `.env`
- generated raw exports

Exit criteria:

- Missing token blocks clearly.
- Sanitized publication writes only bundle files and `publication-provenance.json`.
- Raw artifacts and secrets are rejected or skipped.
- Real publication remains credential-gated until reviewed.

## Phase 6: Encrypted Artifact Backup Gate

Run the adapter first without real tools or credentials. Expected result is a blocked owner action.

When testing a real backend:

- Use a disposable archive repository.
- Use owner-provided credentials.
- Do not commit credentials.
- Store only archive IDs, checksums, artifact metadata, and verification notes in tracker records.
- Keep encrypted archives outside Git.

Artifacts covered:

- PostgreSQL dumps.
- Raw audio.
- Screenshots.
- Generated exports.
- Other ignored local artifacts.

Exit criteria:

- Missing tools or credentials block.
- Real backend test uses disposable storage.
- Archive metadata does not expose secret values or raw artifact contents.

## Phase 7: Guidance Sync Gate

Use fixture repositories or temporary local repositories before real private repositories.

Verify:

- Tracked guidance files are scanned.
- `.env`, `exports`, `backups`, `.git`, caches, key files, and certificate files are excluded.
- Missing or inaccessible private repositories are `auth-blocked`, not empty success.
- Drift classification covers `in-sync`, `stale`, `local-only`, `target-only`, `renamed`, `protected-change`, `auth-blocked`, and `scan-incomplete`.
- Proposal creation is idempotent.
- Proposals require a linked tracker issue, owner, and verification command.
- Protected guidance requires explicit approval text before moving beyond draft.
- Execution defaults to dry-run or auth-blocked behavior.
- Direct pushes are not used for repair.
- Event ingestion deduplicates by repo, branch, commit SHA, and path set.
- Rollback plans are generated but not automatically applied.

Exit criteria:

- Fixture-backed sync behavior passes.
- No real private token is needed.
- No real repository is mutated.
- Protected guidance path requires explicit approval.

## Phase 8: Rule Relevance And Prompt Safety Gate

Verify:

- Inventory scanner finds Codex, Cursor, Claude, prompt, and protected design guidance.
- Missing metadata, duplicate IDs, unsupported harnesses, stale mirrors, and secret-like files are flagged.
- Effective rule resolver includes baseline critical rules.
- Schema, auth, deployment, MCP, UI provenance, backup, and Guidance Sync risks add the right critical rules.
- Prompt linter blocks missing critical rules, missing acceptance criteria, missing verification commands, model/reasoning mismatch warnings, and missing `STOP` handoff.
- Prompt compiler output passes the linter.
- Incident workflow records missed-rule cases without mutating rules automatically.

Exit criteria:

- Prompt linter blocks unsafe prompts.
- Compiled prompt passes.
- Rule resolution remains bounded and explainable.
- Irrelevant rules are not pulled into low-risk work.

## Phase 9: MCP Contract And Mutation Gate

Run MCP tests against disposable data only.

Verify:

- Compact issue search does not dump acceptance criteria by default.
- Full issue details remain opt-in by ID.
- Mutating paths call service-layer logic.
- Issue creation, status update, dependency, sprint creation, sprint assignment, backup health, Guidance Sync proposal, rule resolution, prompt linting, and sync next actions work.
- Outputs stay compact and bounded.

Exit criteria:

- `python -m issue_tracker.mcp.server --smoke` passes.
- `tests/integration/test_mcp_tools.py` passes.
- MCP mutation tests use disposable data only.

## Phase 10: Production-Like Staging Drill

Before UAT or production, run a staging drill:

1. Take a production PostgreSQL dump.
2. Restore it into a separate staging database.
3. Point `DATABASE_URL` at staging only.
4. Disable real `VIBECODING_MIRROR_TOKEN`, webhook secrets, PR-writing credentials, and artifact backup credentials unless specifically testing those paths.
5. Run migrations.
6. Run unit, integration, MCP smoke, and route/browser UAT.
7. Create a recovery bundle from staging.
8. Run recovery bundle dry-run restore.
9. Inspect bundle contents for secrets and raw artifacts.
10. Record evidence in `documentation/uat/YYYY-MM-DD-staging-test.md`.

Exit criteria:

- Migration succeeds on restored production-like data.
- `/health` passes.
- Tests pass.
- Bundle validation and dry-run restore pass.
- No accidental outbound write occurs.

## Phase 11: UAT Deployment Gate

Use the documented local runner pipeline or deployment script only after staging passes.

Required UAT checks:

- Source tree copied without `.git`, caches, `exports/`, `backups/`, `.env`, or credentials.
- Pre-migration dump created under:

```text
/home/akun/issue-tracker/backups/<sha>-<timestamp>/pre-migration.dump
```

- Dump file is non-empty.
- `alembic upgrade head` runs only after backup succeeds.
- App starts.
- `/health` returns database ok.
- MCP smoke passes.
- Browser UAT passes.
- Backup and Guidance Sync pages are usable.

Exit criteria:

- UAT health, MCP smoke, tests, and browser UAT pass.
- Backup path is recorded.
- Any credential-gated real checks are clearly marked blocked owner action, not passed.

## Phase 12: Production Go/No-Go

Do not promote if any of these are true:

- Backup cannot be created, copied, or verified as non-empty.
- Bundle checksum validation fails.
- Dry-run restore reports unsupported schema or corruption.
- Migration fails on restored production-like staging data.
- `/health` is not `{"ok":true,"database":"ok"}`.
- Missing credentials are treated as success.
- Real repository write or backup publication happens without reviewable evidence.
- Any export contains secrets, raw artifacts, dumps, certs, or `.env` content.
- MCP output leaks full issue text or acceptance criteria by default.
- Guidance Sync proposes protected guidance changes without explicit approval text.

Production deployment should run forward-only migrations, preserve existing data, and use manual restore decisions from known-good PostgreSQL backups when needed.

## Evidence To Record

For each test run, record:

- Date.
- Git commit SHA.
- Environment: local, staging, UAT, or production.
- Database target, without secrets.
- Commands run.
- Pass/fail results.
- Backup path and checksum evidence.
- Bundle path and validation result.
- Credential-gated checks and owner actions.
- Known gaps or follow-up issues.

Preferred evidence location:

```text
documentation/uat/YYYY-MM-DD-<environment>-test.md
```
