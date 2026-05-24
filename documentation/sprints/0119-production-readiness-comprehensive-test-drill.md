# Sprint 0119: Production Readiness Comprehensive Test Drill

Status: blocked on production-like staging input

Created: 2026-05-22

Tracker sprint: `0119` Production readiness comprehensive test drill

Source context:

- Comprehensive test plan: `documentation/guides/comprehensive-test-plan.md`
- Sprint 0112 closeout: `documentation/sprints/0112-uat-deploy-comprehensive-test-suite.md`
- Sprint 0112 UAT evidence: `documentation/uat/2026-05-22-sprint-0112-uat-deploy.md`
- Deployment guide: `documentation/guides/deployment.md`
- Manual UAT guide: `documentation/guides/manual-uat.md`
- Sprint 0119 execution evidence: `documentation/uat/2026-05-22-sprint-0119-production-readiness-drill.md`

## Goal

Prove Issue Tracker is ready to run production projects by executing the comprehensive test plan through disposable local data, production-like staging data, UAT deployment gates, and a written production go/no-go report.

This sprint does not authorize production mutation by itself. Production projects are eligible only after the gates below pass or the user explicitly accepts named deferrals.

## Model And Reasoning

Recommended model/reasoning: GPT-5.5 `high`.

Use high reasoning because this sprint covers production-data safety, migration invariants, backup and restore evidence, deployment guards, MCP mutation contracts, and production release decisions.

## Intake And Backlog Review

The active tracker could not be queried during this markdown planning pass because no local tracker container was running and both health checks failed:

```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://192.168.10.20:8000/health
```

Durable Sprint 0112 planning recorded that voice/audio/intake matches `0048`, `0071`, `0074`, `0079`, `0080`, `0081`, `0082`, and `0083` were all `DONE`.

Issue `0120` is the first issue in this sprint and must reconcile the active tracker before implementation continues.

## Backlog

| Order | Tracker ID | Phase | Priority | Issue |
|---:|---|---|---|---|
| 1 | `0120` | Tracker reconciliation | high | Reopen active tracker and synchronize Sprint 0112/0119 records |
| 2 | `0121` | Static and service gate | high | Run Phase 1 static, unit, integration, MCP, and Ruff gates |
| 3 | `0122` | Migration safety | high | Verify migrations on empty and production-like staging databases |
| 4 | `0123` | Disposable browser UAT | high | Run local browser and manual UAT against throwaway data |
| 5 | `0124` | Backup and restore | high | Verify recovery bundle, backup targets, and artifact hygiene |
| 6 | `0125` | Guidance and MCP contracts | high | Verify Guidance Sync, rule relevance, prompt lint, and MCP mutation gates |
| 7 | `0126` | Production-like staging | high | Run the restored-production staging drill with outbound writes disabled |
| 8 | `0127` | UAT deploy drill | high | Deploy the final candidate to UAT and rerun host-level comprehensive checks |
| 9 | `0128` | Go/no-go report | high | Produce production-project readiness evidence and decision handoff |

## Acceptance Criteria

### `0120` Reopen Active Tracker And Synchronize Records

Pass:

- The intended active tracker database is identified before mutation.
- Sprint `0112` is closed in the tracker with close evidence matching this markdown record.
- Sprint `0119` and issues `0120` through `0128` exist in the tracker with pass/fail acceptance criteria, model/reasoning guidance, verification commands, and STOP handoffs.
- Active tracker search for `To process`, `voice-feedback`, `audio`, `intake`, and `clarify` is rerun and either included in this sprint or explicitly deferred with a reason.

Fail:

- The tracker database is ambiguous, inaccessible, or appears to be a fresh empty stack.
- Any voice/audio/intake issue is skipped without an explicit defer decision.

Verification:

```bash
curl -fsS http://127.0.0.1:8000/health || curl -fsS http://192.168.10.20:8000/health
```

STOP: Do not continue tracker-mutating work until the intended active tracker database is confirmed.

### `0121` Run Phase 1 Static, Unit, Integration, MCP, And Ruff Gates

Pass:

- Compose config and build succeed under an isolated project name.
- Unit and integration tests pass.
- MCP smoke lists the expected compact project, issue, sprint, category, Guidance Sync, backup, rule, prompt, and sync tools.
- Ruff passes with `--no-cache`.
- Dev health is checked before and after the preflight if the dev host is running.

Fail:

- Any test or lint gate fails.
- The preflight disrupts an existing dev stack.

Verification: run Phase 1 commands from `documentation/guides/comprehensive-test-plan.md`.

STOP: Fix failing code or tests before proceeding to migration or UAT gates.

### `0122` Verify Migration Safety

Pass:

- Empty database `alembic upgrade head` succeeds.
- Restored production-like staging database `alembic upgrade head` succeeds.
- Representative project, issue, sprint, guidance, and audit records remain present after migration.
- No downgrade, drop, truncate, reset, recreate, or upward data-copy command is used.

Fail:

- Migration deletes tracker data or requires a destructive recovery step.
- A production database is used for test migration.

Verification: run Phase 2 commands from the comprehensive test plan and record row-count evidence.

STOP: Block production readiness until migration behavior is understood and fixed.

### `0123` Run Disposable Browser And Manual UAT

Pass:

- Local browser UAT passes against disposable data.
- Manual UAT covers setup/login, project, category, issue, dependency, sprint, closeout, issue log, backlog, board, releases, intake, planning, backup, and Guidance Sync navigation.
- Desktop and mobile usability are checked.
- No secrets appear in UI output.

Fail:

- Any primary workflow is unusable.
- Test data or generated artifacts are committed.

Verification: run Phase 3 commands from the comprehensive test plan and record the manual UAT note path.

STOP: Fix user-visible blockers before production-like staging.

### `0124` Verify Backup, Restore, And Artifact Hygiene

Pass:

- Recovery bundle generation succeeds for fake data.
- Checksums are recorded and verified.
- Backup target planning reports owner-action blockers when credentials or targets are missing.
- Generated exports, backups, dumps, screenshots, raw audio, certs, and credentials remain out of git.

Fail:

- A backup path claims success without a usable artifact.
- Secrets or generated artifacts are staged or committed.

Verification: run the backup and recovery phases from the comprehensive test plan.

STOP: Treat missing backup credentials as an owner-action blocker, not a passed backup gate.

### `0125` Verify Guidance, Rule, Prompt, And MCP Contracts

Pass:

- Guidance Sync dry-run and proposal behavior remains review-first.
- Rule relevance and prompt lint checks classify applicability without mutating protected guidance.
- MCP mutating tools use service-layer operations and return compact output by default.
- Prompt compile/lint behavior produces clear failures for missing acceptance criteria, verification, or STOP sections.

Fail:

- Guidance Sync or MCP mutates external repositories without review.
- MCP output becomes too verbose by default.

Verification: run the Guidance Sync, rule relevance, prompt lint, and MCP phases from the comprehensive test plan.

STOP: Fix contract drift before UAT deployment.

### `0126` Run Production-Like Staging Drill

Pass:

- A separate staging PostgreSQL database is restored from a production dump.
- Outbound write credentials are disabled.
- Migration, health, browser smoke, backup planning, and representative project read checks pass.
- Secrets/session sanitization expectations are recorded.

Fail:

- The production database is pointed at by test commands.
- Outbound repository, backup, email, or token-bearing writes remain enabled.

Verification: record staging database identity, sanitized credential state, row-count before/after evidence, and command output summaries.

STOP: Require explicit owner action if no production dump or staging target is available.

### `0127` Deploy Final Candidate To UAT And Rerun Host Gates

Pass:

- `git status` is clean or intended drift is explicitly resolved before dispatch.
- Exact branch and SHA are stated before workflow dispatch.
- Workflow input `expected_deploy_sha` equals the candidate SHA.
- UAT pre-migration backup is created and verified non-empty.
- UAT health, tests, MCP smoke, Ruff, and browser UAT pass.
- UAT data is preserved; no reset, drop, restore-from-dev, or volume replacement occurs.

Fail:

- Local branch differs from remote ref or contains uncommitted intended changes.
- UAT backup, migration, health, or browser UAT fails.

Verification: run the UAT deployment commands from the comprehensive test plan and record workflow run ID, SHA, backup path, and health response.

STOP: Do not dispatch production while UAT source-of-truth or health evidence is incomplete.

### `0128` Produce Production-Project Readiness Report

Pass:

- A dated readiness note summarizes every gate as pass, fail, or blocked with evidence.
- Remaining risks and owner-action blockers are listed.
- Production rollout decision is one of: ready for production-project use, blocked by named owner action, or not ready due to named regressions.
- If ready, the report states the exact deployable branch/SHA and any required pre-production backup command.

Fail:

- Any gate is summarized without evidence.
- Production readiness is claimed while staging or UAT is blocked.

Verification: create the readiness note under `documentation/uat/` and link it from this sprint.

STOP: Sprint 0119 is not complete until every issue is done or the user explicitly accepts named deferrals.

## Dependency-Aware Execution Plan

1. Reconcile tracker state first (`0120`).
2. Run local static/service gates (`0121`) before data-bearing checks.
3. Run migration safety (`0122`) before browser, backup, or UAT release claims.
4. Run disposable browser/manual UAT (`0123`) before production-like staging.
5. Verify backup/recovery and artifact hygiene (`0124`) before any data refresh or UAT deploy.
6. Verify Guidance Sync, rule, prompt, and MCP contracts (`0125`) before production-like staging or production-project use.
7. Run production-like staging (`0126`) before UAT redeploy.
8. Run final UAT deployment drill (`0127`) from an exact pushed SHA.
9. Write the production readiness go/no-go report (`0128`).

## STOP

Sprint 0119 may close only when the comprehensive production-readiness drill is complete and the production-project readiness report is written.

If blocked, the handoff must name the specific owner action: active tracker unavailable, production dump unavailable, staging database unavailable, credentials missing, backup target missing, browser-capable test environment missing, failed migration, failed backup, failed UAT deployment, or product regression.

## Execution Update - 2026-05-22

Sprint execution started and completed `0120` tracker reconciliation plus `0121` static/service gates. Local disposable and empty-database Alembic checks for `0122` passed in the isolated preflight stack.

Current STOP: `0122` cannot pass without an owner-provided production dump and a separate production-like staging PostgreSQL target. Do not continue to disposable browser UAT, staging, UAT redeploy, or production-project readiness until that input is available or the user explicitly accepts a named deferral.

Follow-up execution sprint: `documentation/sprints/0129-uat-as-staging-dev-seed-production-readiness.md` replaces the missing production-dump assumption with the user-approved pre-production strategy: use UAT as staging and seed it from the current dev tracker dataset because the app has no production data yet.
