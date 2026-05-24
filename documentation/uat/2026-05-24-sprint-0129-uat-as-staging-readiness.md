# Sprint 0129 UAT-As-Staging Readiness Evidence

Date: 2026-05-24

Status: in progress after UAT refresh.

Decision: not ready for production-project use yet. UAT has been backed up and refreshed from the dev seed, but candidate deployment, UAT migrations, full UAT suite, backup/recovery verification, and readiness decision still need evidence.

## Source And Target

- Source environment: `dev`.
- Target environment: `uat`.
- Target host: `app-uat` / `192.168.10.26`.
- UAT overwrite semantics: destructive to UAT, non-destructive to production.
- Production: not touched.
- Local branch: `deploy/app-host-targets-0112`.
- Local HEAD before deployment commit: `35de77cb4922543f2ca6e77d9ed7f1e10238fb91`.
- Local git state before deployment gate: dirty with intended sprint/readiness documentation updates.

## Tracker State

- Tracker project `issue-tracker` exists with project id `1`.
- Tracker Sprint `0129` exists and is active with nine assigned issues.
- Issues `0130` through `0138` exist with acceptance criteria, verification commands, model/reasoning guidance, and STOP handoffs.
- Remaining issue state after this run:
  - `0130`: done before this run.
  - `0131`: done by this run.
  - `0132`: done by this run.
  - `0133`: done by this run.
  - `0134` through `0138`: still in progress.

## Intake Search

Active tracker search for `To process`, `voice-feedback`, `audio`, `intake`, and `clarify` found only closed historical voice/intake-related issues:

- `0048`, `0071`, `0074`, `0079`, `0080`, `0081`, `0082`, and `0083`.

Decision: no open intake items were added to Sprint `0129`; closed historical intake items are deferred because they do not block the UAT-as-staging refresh.

## Gate Evidence

### `0130` Scope Lock

Result: pass.

Evidence:

- Dev health: `curl -fsS http://127.0.0.1:8000/health` returned `{"ok":true,"database":"ok"}`.
- Source recorded as `dev`.
- Target recorded as `uat`.
- UAT overwrite recorded as destructive to UAT and non-destructive to production.
- Tracker Sprint `0129` and issues `0130` through `0138` verified.

### `0131` Dev Seed

Result: pass.

Evidence:

- Dev health returned `{"ok":true,"database":"ok"}`.
- Representative records verified before dump:
  - `issue-tracker` project exists.
  - Sprint `0129` exists.
  - Sprint `0119` exists.
  - Sprint `0112` is closed.
  - Issues `0130` through `0138` exist.
- Dev database counts:
  - projects: `21`
  - issues: `216`
  - sprints: `26`
  - categories: `129`
  - issue events: `594`
  - issue log entries: `0`
  - guidance sources/snapshots/sync runs/audit entries: `0`
- Dev `issue-tracker` project counts:
  - issues: `128`
  - sprints: `10`
  - categories: `17`
- Dump command:

```bash
docker compose -f deployment/docker-compose.local.yml exec postgres pg_dump -U issue_tracker -d issue_tracker -Fc -f /tmp/dev-seed-20260524042639.dump
docker compose -f deployment/docker-compose.local.yml cp postgres:/tmp/dev-seed-20260524042639.dump backups/sprint-0129/dev-seed-20260524042639.dump
```

- Dump path: `backups/sprint-0129/dev-seed-20260524042639.dump`.
- Dump size: `129K`.
- Dump sha256: `7c14c00aad29a2b4cfa29f192f42286d35e6364eae933cf26c02d7a4a14d06cd`.
- Artifact hygiene: `backups/` is ignored by `.gitignore`.
- Tracker issue `0131` closed with dump evidence.

### `0132` UAT Protection

Result: pass.

Evidence:

- UAT health: `curl -fsS http://192.168.10.26:8000/health` returned `{"ok":true,"database":"ok"}`.
- SSH target identity: `ssh ... akun@192.168.10.26 hostname` returned `app-uat`.
- Current UAT release before refresh: `/home/akun/issue-tracker/releases/cf6257727ab908291aba1873c49167f39fc2cdfd-20260522060939`.
- Current UAT migration before refresh: `0003_guidance_audit_events`.
- Current UAT database before refresh:
  - projects: `2`
  - project rows: `test`, `Browser UAT Project 20260522061057`
- Pre-refresh backup command created a PostgreSQL custom-format dump outside Git:

```bash
ssh akun@192.168.10.26 'cd /home/akun/issue-tracker/current && docker compose -f deployment/docker-compose.local.yml exec -T postgres pg_dump -U issue_tracker -d issue_tracker -Fc -f /tmp/pre-dev-seed-refresh-20260524043200.dump'
```

- UAT pre-refresh backup path: `/home/akun/issue-tracker/backups/dev-seed-refresh-20260524043200/pre-dev-seed-refresh.dump`.
- UAT backup size: `72K`.
- UAT backup sha256: `bf371d6bcc4d3488af9dec0070c60955d4b9e6802ceecc130ac3d2ff1b79e268`.

### `0133` UAT Refresh

Result: pass.

Evidence:

- Dev seed copied to UAT path: `/home/akun/issue-tracker/backups/dev-seed-refresh-20260524043200/dev-seed-20260524042639.dump`.
- Copied seed sha256 matched dev seed: `7c14c00aad29a2b4cfa29f192f42286d35e6364eae933cf26c02d7a4a14d06cd`.
- Restore target: only `app-uat` / `192.168.10.26`, database `issue_tracker`.
- Restore sequence:
  - stopped UAT app container,
  - terminated UAT `issue_tracker` database sessions,
  - dropped and recreated only the UAT `issue_tracker` database,
  - restored the copied dev seed dump,
  - restarted the UAT app container.
- Post-restore health: `curl -fsS http://192.168.10.26:8000/health` returned `{"ok":true,"database":"ok"}`.
- Post-restore UAT database counts match the dev seed:
  - projects: `21`
  - issues: `216`
  - sprints: `26`
  - categories: `129`
  - issue events: `594`
  - issue log entries: `0`
  - guidance sources/snapshots/sync runs/audit entries: `0`
- Post-restore UAT `issue-tracker` project counts match the dev seed:
  - issues: `128`
  - sprints: `10`
  - categories: `17`
- Representative checks passed:
  - Sprint `0129` exists.
  - Sprint `0119` exists.
  - Sprint `0112` is closed.
  - Issues `0130` through `0138` exist.

### `0134` Through `0138`

Result: not run.

Reason: pending. The next gate is to commit/push intended documentation state, deploy exact candidate SHA to UAT with `expected_deploy_sha`, and verify health.

## Owner Action

No owner action is currently required for `0132` or `0133`.

## STOP

Sprint `0129` remains active. Production-project readiness is blocked until `0134` through `0138` pass or the user explicitly accepts named deferrals.
