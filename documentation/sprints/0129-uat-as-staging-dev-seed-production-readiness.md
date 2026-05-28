# Sprint 0129: UAT-As-Staging Dev Seed Production Readiness

Status: complete

Created: 2026-05-24

Tracker sprint: `0129` UAT-as-staging dev seed production readiness drill

Source context:

- Blocked predecessor: `documentation/sprints/0119-production-readiness-comprehensive-test-drill.md`
- Sprint 0119 evidence: `documentation/uat/2026-05-22-sprint-0119-production-readiness-drill.md`
- Sprint 0129 execution evidence: `documentation/uat/2026-05-24-sprint-0129-uat-as-staging-readiness.md`
- Comprehensive test plan: `documentation/guides/comprehensive-test-plan.md`
- Backup and restore guide: `documentation/guides/backup-restore.md`
- Deployment guide: `documentation/guides/deployment.md`
- Manual UAT guide: `documentation/guides/manual-uat.md`

## Goal

Use UAT as the staging environment for the brand-new Issue Tracker app by refreshing UAT from the current dev tracker dataset, then run the full production-readiness suite against UAT before approving production-project use.

This sprint does not use production data because no production data exists yet. The current dev tracker database is the representative seed dataset because it contains the dogfood project, historical issues, sprints, categories, close metadata, guidance records, backup records, and Sprint `0119` planning state.

## Model And Reasoning

Recommended model/reasoning: GPT-5.5 `high`.

Use high reasoning because this sprint intentionally overwrites UAT data, verifies backup and restore evidence, runs migrations against representative data, deploys an exact candidate SHA, and makes a production-readiness decision.

## Scope Decision

User decision: use UAT as staging and use the current dev issue-tracker database as the seed dataset because this is a new app with no production database yet.

Safety interpretation:

- This is a dev-to-UAT data refresh, not a normal UAT deploy.
- UAT data will be overwritten only after the target is named and backed up.
- Production is not touched.
- Generated dumps, backups, exports, screenshots, raw audio, local certs, and credentials stay out of Git.

## Backlog

| Order | Tracker ID | Phase | Priority | Issue |
|---:|---|---|---|---|
| 1 | `0130` | Scope lock | high | Confirm UAT-as-staging refresh scope and safety checks |
| 2 | `0131` | Dev seed | high | Create and verify dev seed dump from current tracker data |
| 3 | `0132` | UAT protection | high | Back up current UAT database and record restore metadata |
| 4 | `0133` | UAT refresh | high | Restore dev seed dump into UAT and verify database identity |
| 5 | `0134` | Candidate deploy | high | Deploy exact dev candidate SHA to UAT |
| 6 | `0135` | Migration and data checks | high | Run UAT migrations and representative data survival checks |
| 7 | `0136` | Full UAT suite | high | Run full browser, manual, route, MCP, and service UAT suite |
| 8 | `0137` | Backup and artifact hygiene | high | Verify recovery bundle, backup blockers, and artifact hygiene on UAT |
| 9 | `0138` | Readiness decision | high | Write go/no-go report and close or block production-project readiness |

## Acceptance Criteria

### `0130` Confirm UAT-As-Staging Refresh Scope And Safety Checks

Pass:

- Tracker Sprint `0129` and issues `0130` through `0138` exist with pass/fail acceptance criteria, verification commands, model/reasoning guidance, and STOP handoffs.
- The target environment is explicitly recorded as `uat`.
- The source environment is explicitly recorded as `dev`.
- The plan records that UAT overwrite is destructive to UAT but non-destructive to production.
- Active tracker search for `To process`, `voice-feedback`, `audio`, `intake`, and `clarify` is rerun and included or explicitly deferred.

Fail:

- The source or target is ambiguous.
- UAT overwrite is treated as a normal deploy.
- Intake items are skipped without a recorded decision.

Verification:

```bash
curl -fsS http://127.0.0.1:8000/health
```

STOP: Do not create or restore dumps until source `dev`, target `uat`, and UAT overwrite semantics are recorded.

### `0131` Create And Verify Dev Seed Dump

Pass:

- Dev health returns `{"ok":true,"database":"ok"}`.
- Dev database identity and project row counts are recorded.
- A PostgreSQL dump is created from dev into ignored local storage.
- Dump file is non-empty and has a checksum.
- Representative records exist before dump: project `issue-tracker`, Sprint `0129`, Sprint `0119`, issues `0130` through `0138`, closed Sprint `0112`, categories, guidance records, and issue events.

Fail:

- Dev DB is unhealthy.
- Dump is missing, empty, or stored in Git-tracked content.
- Representative records are missing before dump.

Verification:

```bash
docker compose -f deployment/docker-compose.local.yml exec postgres pg_dump -U issue_tracker -Fc issue_tracker
```

STOP: Do not touch UAT until the dev seed dump is verified.

### `0132` Back Up Current UAT Database And Record Restore Metadata

Pass:

- UAT host, branch/SHA, health response, and database identity are recorded before refresh.
- Current UAT database backup is created before overwrite.
- UAT backup is non-empty and has a checksum.
- Backup path is outside Git.

Fail:

- UAT health or database identity cannot be verified.
- UAT backup fails or is empty.
- Backup path could be committed.

Verification:

```bash
ssh <uat-host> 'pg_dump ... > backups/<timestamp>/pre-dev-seed-refresh.dump && test -s backups/<timestamp>/pre-dev-seed-refresh.dump'
```

STOP: Do not overwrite UAT without a verified UAT backup.

### `0133` Restore Dev Seed Dump Into UAT And Verify Database Identity

Pass:

- Dev seed dump is copied to UAT through a reviewed path.
- UAT database is restored from the dev seed dump.
- Restore command targets UAT only.
- Post-restore health confirms database connectivity.
- UAT row counts match the dev seed for representative tables.

Fail:

- Restore target is ambiguous.
- Any command points at production.
- UAT health fails after restore.

Verification:

```bash
ssh <uat-host> 'pg_restore ... && curl -fsS http://127.0.0.1:8000/health'
```

STOP: Fix restore or health failures before deploying or running UAT tests.

### `0134` Deploy Exact Dev Candidate SHA To UAT

Pass:

- Local `git status` is clean or intended documentation/tracker changes are committed.
- The exact branch and commit SHA are stated before workflow dispatch.
- The candidate SHA is pushed to the remote ref.
- UAT deploy uses `expected_deploy_sha`.
- UAT data is preserved during code deploy after the refresh.

Fail:

- Local branch differs from remote ref.
- Intended changes are uncommitted.
- Workflow deploys a different SHA.
- Deploy resets, drops, or replaces the refreshed UAT DB.

Verification:

```bash
git status --short --branch
git rev-parse HEAD
gh workflow run <uat-workflow> --ref <branch> -f expected_deploy_sha=<sha>
```

STOP: Do not run the full UAT suite until the exact candidate SHA is deployed and healthy.

### `0135` Run UAT Migrations And Representative Data Survival Checks

Pass:

- `alembic upgrade head` runs on UAT.
- UAT `/health` passes after migration.
- Representative records survive migration: project `issue-tracker`, Sprint `0129`, Sprint `0119`, issues `0130` through `0138`, closed Sprint `0112`, categories, guidance records, issue events, and close metadata.
- No downgrade, truncate, reset, production restore, or UAT-to-production data copy is used.

Fail:

- Migration fails.
- Representative records are missing after migration.
- Any destructive command targets the wrong environment.

Verification:

```bash
ssh <uat-host> 'cd /home/akun/issue-tracker && docker compose -f deployment/docker-compose.app.yml run --rm app alembic upgrade head'
curl -fsS <uat-url>/health
```

STOP: Fix migration or data survival failures before manual/browser UAT.

### `0136` Run Full Browser, Manual, Route, MCP, And Service UAT Suite

Pass:

- Automated UAT/browser tests pass against UAT.
- Manual path covers setup/login as applicable, project, category, issue, dependency, sprint, closeout, issue log, backlog, board, releases, intake, planning, backup, and Guidance Sync navigation.
- Desktop and mobile usability are checked.
- MCP smoke passes against UAT.
- No secrets appear in UI or logs.

Fail:

- Any primary workflow is unusable.
- Browser tests fail without triage.
- UAT exposes secrets or raw ignored artifacts.

Verification:

```bash
RUN_BROWSER_UAT=1 python -m pytest tests/e2e/test_browser_uat.py
python -m issue_tracker.mcp.server --smoke
```

STOP: Fix user-visible blockers or record explicit user-accepted deferrals before readiness reporting.

### `0137` Verify Recovery Bundle, Backup Blockers, And Artifact Hygiene On UAT

Pass:

- Recovery bundle export succeeds for the refreshed UAT project.
- Restore dry-run succeeds or reports expected reviewable blockers.
- Missing external backup credentials are reported as owner-action blockers, not success.
- Generated dumps, backups, exports, screenshots, raw audio, local certs, and credentials remain ignored and unstaged.

Fail:

- Backup path claims success without a usable artifact.
- Secrets or generated artifacts are staged or committed.
- Missing credentials are treated as pass.

Verification:

```bash
issue-tracker export-recovery-bundle 1 exports/recovery-bundles/issue-tracker/uat-seed
issue-tracker restore-recovery-bundle exports/recovery-bundles/issue-tracker/uat-seed --dry-run
git status --short
```

STOP: Do not approve production-project use until backup and artifact hygiene evidence exists.

### `0138` Write Go/No-Go Report And Close Or Block Production-Project Readiness

Pass:

- A dated UAT/staging readiness note summarizes every Sprint `0129` gate as pass, fail, or blocked with evidence.
- Remaining risks and owner-action blockers are listed.
- Decision is one of: ready for production-project use, blocked by named owner action, or not ready due to named regressions.
- If ready, the report states exact branch/SHA and required pre-production backup command.
- Sprint `0129` is closed only if every issue is done or the user explicitly accepts named deferrals.

Fail:

- Any gate is summarized without evidence.
- Production readiness is claimed while UAT refresh, migration, UAT suite, or backup hygiene is blocked.

Verification:

```bash
test -s documentation/uat/YYYY-MM-DD-sprint-0129-uat-as-staging-readiness.md
```

STOP: Sprint `0129` remains active until the readiness report is written and all issues are done or explicitly deferred.

## Dependency-Aware Execution Plan

1. Lock scope and safety semantics (`0130`).
2. Create and verify dev seed dump (`0131`).
3. Back up current UAT (`0132`).
4. Restore dev seed into UAT (`0133`).
5. Deploy exact candidate SHA to UAT (`0134`).
6. Run UAT migration and representative data checks (`0135`).
7. Run the full UAT suite (`0136`).
8. Verify backup/recovery and artifact hygiene (`0137`).
9. Write readiness report and close or block the sprint (`0138`).

## STOP

Do not overwrite UAT until the target `uat`, source `dev`, and verified UAT pre-refresh backup are recorded.

Do not approve production-project use until UAT-as-staging refresh, migration, full UAT suite, backup/recovery evidence, and go/no-go report all pass or the user explicitly accepts named deferrals.
