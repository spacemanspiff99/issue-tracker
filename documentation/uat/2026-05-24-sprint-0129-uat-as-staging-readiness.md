# Sprint 0129 UAT-As-Staging Readiness Evidence

Date: 2026-05-24

Status: complete.

Decision: ready for production-project use with one owner-action caveat: external artifact backup tooling such as `restic`, `borg`, or `rclone` is not installed/configured on UAT. PostgreSQL backups, recovery bundle export, recovery dry-run, migration, health, MCP, route, and browser UAT gates passed.

## Source And Target

- Source environment: `dev`.
- Target environment: `uat`.
- Target host: `app-uat` / `192.168.10.26`.
- UAT overwrite semantics: destructive to UAT, non-destructive to production.
- Production: not touched.
- Local branch: `deploy/app-host-targets-0112`.
- Local HEAD before deployment commit: `35de77cb4922543f2ca6e77d9ed7f1e10238fb91`.
- Deployment commit: `35bd14f81586203912cab60f66a17f04886e6ba5`.
- Deployment workflow run: `26366490777`.
- Deployment workflow URL: `https://github.com/spacemanspiff99/issue-tracker/actions/runs/26366490777`.

## Tracker State

- Tracker project `issue-tracker` exists with project id `1`.
- Tracker Sprint `0129` exists and is active with nine assigned issues.
- Issues `0130` through `0138` exist with acceptance criteria, verification commands, model/reasoning guidance, and STOP handoffs.
- Remaining issue state after this run:
  - `0130`: done before this run.
  - `0131`: done by this run.
  - `0132`: done by this run.
  - `0133`: done by this run.
  - `0134`: passed by workflow run `26366490777`.
  - `0135`: passed by workflow migration and post-deploy data survival checks.
  - `0136`: passed by workflow tests, MCP smoke, and browser UAT.
  - `0137`: passed with artifact backup owner-action blocker recorded.
  - `0138`: this report records the go decision.

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

### `0134` Candidate Deploy

Result: pass.

Evidence:

- Documentation/source-of-truth commit created and pushed before deploy:
  - branch: `deploy/app-host-targets-0112`
  - SHA: `35bd14f81586203912cab60f66a17f04886e6ba5`
- Workflow dispatch:

```bash
gh workflow run local-pipeline.yml --ref deploy/app-host-targets-0112 \
  -f expected_deploy_sha=35bd14f81586203912cab60f66a17f04886e6ba5 \
  -f uat_host=192.168.10.26 \
  -f prod_host=192.168.10.27 \
  -f deploy_user=akun \
  -f deploy_path=/home/akun/issue-tracker \
  -f prod_env_file=/home/akun/issue-tracker/prod.env \
  -f deploy_prod=false
```

- First run `26365924080` was canceled after the deploy step spent about 14 minutes in the Docker build. Direct evidence showed the build was not deadlocked; it was rebuilding the Playwright dependency layer after a README/doc change invalidated the Docker cache.
- Retry run `26366490777` passed.
- Workflow verified:
  - `GITHUB_REF`: `refs/heads/deploy/app-host-targets-0112`
  - `GITHUB_SHA`: `35bd14f81586203912cab60f66a17f04886e6ba5`
  - `EXPECTED_DEPLOY_SHA`: `35bd14f81586203912cab60f66a17f04886e6ba5`
  - target environment: `uat`
  - target host: `192.168.10.26`
  - target hostname: `app-uat`
- Deployed release path: `/home/akun/issue-tracker/releases/35bd14f81586203912cab60f66a17f04886e6ba5-20260524162322`.
- UAT pre-migration backup path created by workflow: `/home/akun/issue-tracker/backups/35bd14f81586203912cab60f66a17f04886e6ba5-20260524162322/pre-migration.dump`.
- UAT pre-migration backup size: `129K`.
- UAT pre-migration backup sha256: `2dcc4149c66f833a19f8579c27ca25f9037efd33a0f1d7c0c6df549fdec47762`.
- Post-deploy health: `{"ok":true,"database":"ok"}`.
- Production deploy was disabled: `deploy_prod=false`.

### `0135` Migration And Data Checks

Result: pass.

Evidence:

- Workflow ran `alembic upgrade head` against UAT after the pre-migration backup.
- UAT migration revision after deploy: `0003_guidance_audit_events`.
- Post-deploy UAT database counts:
  - projects: `22`
  - issues: `219`
  - sprints: `27`
  - categories: `135`
  - issue events: `600`
- Count increases after seed are expected from the browser UAT project created by the workflow.
- Representative survival checks passed:
  - Sprint `0129` exists.
  - Sprint `0119` exists.
  - Sprint `0112` is closed and has close metadata.
  - Issues `0130` through `0138` exist.
  - Categories exist.
  - Issue events exist.
- No downgrade, truncate, reset, production restore, or UAT-to-production copy was used after the UAT refresh.

### `0136` Full UAT Suite

Result: pass.

Evidence:

- Workflow full test gate: `47 passed, 1 skipped, 1 warning in 13.19s`.
- Ruff gate: `All checks passed!`.
- MCP smoke returned `{"ok": true}` with project, issue, sprint, category, Guidance Sync, backup, rule, prompt, and sync tools.
- Browser UAT gate: `1 passed, 1 warning in 30.68s`.
- Browser UAT covered setup/login, project creation, recommended taxonomy/categories, issue AC validation, issue creation, dependencies, sprint creation/assignment, issue closeout, sprint progress, search, backlog, board, releases, Guidance Sync, intake recording, backup page, and desktop/mobile viewports.
- No secret exposure was observed in the captured workflow output.

### `0137` Backup And Artifact Hygiene

Result: pass with owner-action caveat.

Evidence:

- UAT recovery bundle export succeeded:

```bash
docker compose -f deployment/docker-compose.local.yml run --rm app issue-tracker export-recovery-bundle 1 exports/recovery-bundles/issue-tracker/uat-seed-20260524
```

- UAT recovery dry-run restore succeeded:

```json
{"errors": [], "ok": true, "project_name": "issue-tracker", "status": "dry-run", "would_create": {"categories": 17, "dependencies": 16, "guidance_drifts": 0, "guidance_proposals": 0, "guidance_snapshots": 0, "guidance_sources": 0, "issue_logs": 0, "issues": 128, "sprints": 10}, "would_require_category_mapping": true}
```

- Recovery bundle files are under ignored `exports/`.
- Bundle hygiene check found no `*.dump`, `*.key`, `*.env`, or `*.webm` files in the recovery bundle.
- UAT release has no `.git` directory.
- Local generated dev seed dump remains ignored by `.gitignore` under `backups/`.
- External artifact backup probe result:

```text
ArtifactBackupResult(status='blocked', backend='restic', archive_id=None, blocked_reason='restic is not installed on this host', ... next_action='Owner action required: restic is not installed on this host.')
```

Owner-action caveat: install/configure a chosen encrypted artifact backup backend before relying on UAT for raw generated artifacts. This does not block PostgreSQL pre-migration backup or sanitized recovery bundle use.

### `0138` Readiness Decision

Result: pass.

Decision: ready for production-project use.

Required pre-production backup command before any production deployment:

```bash
ssh akun@192.168.10.27 'cd /home/akun/issue-tracker/current && docker compose -f deployment/docker-compose.local.yml exec -T postgres pg_dump -U issue_tracker -d issue_tracker -Fc -f /tmp/pre-production-project-use.dump'
```

Then copy that dump to the production host backup folder, verify it is non-empty, checksum it, and only then run forward-only migrations.

## Owner Action

- Install/configure an encrypted external artifact backup backend such as `restic`, `borg`, or `rclone` if UAT or production will retain raw generated artifacts outside PostgreSQL/sanitized recovery bundles.
- Consider optimizing the Dockerfile so documentation-only changes do not invalidate the Playwright dependency layer; run `26366490777` passed, but the rebuild took 17 minutes.

## STOP

Sprint `0129` can close after the tracker issues are closed with this evidence. No production data was touched.
