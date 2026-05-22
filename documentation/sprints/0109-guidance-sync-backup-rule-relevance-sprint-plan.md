# Sprint Plan: Guidance Sync, Backup, And Rule Relevance

Status: Sprint 1 complete; remaining work consolidated into Sprint `0110`

Backlog source: `documentation/planning/GUIDANCE_SYNC_BACKUP_AND_RULE_RELEVANCE_BACKLOG.md`

Oversized execution sprint: `documentation/sprints/0110-overnight-guidance-sync-backup-rule-relevance-completion.md`

Tracker issues: `0085` through `0108`

Planning date: 2026-05-19

## Product Goal

Make Issue Tracker reliable as the control plane for recoverable tracker state and relevant cross-project AI guidance.

This means:

- Backups are portable, reviewable, restorable, and not proprietary to Issue Tracker.
- `vibecoding` can hold sanitized recovery bundles and rule manifests.
- Raw artifacts and database dumps are backed up through encrypted provider-neutral tooling, not Git.
- Rule sync stops being path-copying and becomes applicability-aware, branch-aware, and fail-closed for critical rules.
- Prompts can be linted before use so critical guidance is not silently missed.

## Current Backlog Completeness

The backlog is complete for the current product question. It covers:

- Backup threat model and recovery objectives.
- Portable sanitized recovery bundle format.
- Vibecoding backup target workflow.
- Encrypted artifact backup adapter.
- Restore verifier and restore drills.
- Backup health and MCP visibility.
- Rule metadata, project-type packs, and critical-rule baseline.
- Effective rule resolver and prompt coverage linter.
- Prompt compiler and missed-rule incident loop.
- Remote GitHub scanning, side-by-side proposal review, PR execution, webhook/polling ingestion, version manifests, and cross-project dashboard.
- Regression and MCP quality gates.

The known non-goals are also explicit:

- Do not store raw dumps, raw audio, screenshots, certs, `.env`, or credentials in GitHub.
- Do not silently overwrite child project rules.
- Do not rely on prompt authors remembering rule paths manually.

## Tracker Intake Check

The active tracker was checked before planning. Voice/audio/intake issues matching `To process`, `voice-feedback`, `audio`, `intake`, or `clarify` were all already done: `0048`, `0071`, `0074`, `0079`, `0080`, `0081`, `0082`, and `0083`.

No intake work is deferred from this sprint plan.

## Sprint 1: Portable Backup Foundation

Status: complete in tracker sprint `0109`

Recommended model/reasoning: GPT-5.5 `high`

Tracker issues:

| Order | Issue | Title | Reason |
|---:|---|---|---|
| 1 | `0085` | Backup threat model, recovery objectives, and retention policy | Establish recoverability boundaries before implementation. |
| 2 | `0086` | Portable recovery bundle schema | Define the durable format before CLI/UI work. |
| 3 | `0087` | Export recovery bundle command and UI | Build the first usable sanitized export path. |
| 4 | `0090` | Restore verifier and dry-run importer | Prove bundles can be validated before mutation. |
| 5 | `0091` | Backup health dashboard and audit trail | Expose health and evidence through web/MCP. |

Implementation shape:

- Start with docs and schema/service design.
- Add tests before expanding UI.
- Keep existing JSON import/export compatible.
- Do not touch remote GitHub or encrypted artifact execution yet.

Required verification:

```bash
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/unit/ tests/integration/test_cli_import_export.py
docker compose -f deployment/docker-compose.local.yml run --rm app python -m issue_tracker.mcp.server --smoke
docker compose -f deployment/docker-compose.local.yml run --rm app python -m ruff check --no-cache .
```

STOP:

- Stop when sanitized bundle export, dry-run verification, backup dashboard evidence, and MCP health are implemented and tested.
- If schema changes are needed, also run `alembic upgrade head` on an empty database and record evidence.

Close evidence from 2026-05-19:

- Tracker sprint `0109` was created for Portable Backup Foundation and closed.
- Tracker issues `0085`, `0086`, `0087`, `0090`, and `0091` were closed.
- Implemented portable recovery bundle service, sanitized bundle export, manifest checksum validation, dry-run restore summary, backup health summary, backup page evidence, CLI commands, and compact MCP `backup.health`.
- No schema migration was needed.
- Active tracker bundle exported to `exports/recovery-bundles/issue-tracker/latest/manifest.json`.
- Dry-run restore returned `ok=true` with project `issue-tracker`, `103` issues, `6` sprints, `17` categories, and checksum validation passing.

Verification:

```bash
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/integration/test_cli_import_export.py tests/integration/test_mcp_tools.py tests/integration/test_web_routes.py
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/unit/
docker compose -f deployment/docker-compose.local.yml run --rm app python -m issue_tracker.mcp.server --smoke
docker compose -f deployment/docker-compose.local.yml run --rm app python -m ruff check --no-cache .
docker compose -f deployment/docker-compose.local.yml run --rm app issue-tracker export-recovery-bundle 1 exports/recovery-bundles/issue-tracker/latest
docker compose -f deployment/docker-compose.local.yml run --rm app issue-tracker restore-recovery-bundle exports/recovery-bundles/issue-tracker/latest --dry-run
```

Results:

- Focused integration tests: `20 passed`.
- Unit tests: `18 passed`.
- MCP smoke: passed and listed `backup.health`.
- Ruff: all checks passed.
- Recovery bundle dry run: passed.

## Sprint 2: Backup Destinations And Artifact Safety

Recommended model/reasoning: GPT-5.5 `high`

Tracker issues:

| Order | Issue | Title | Reason |
|---:|---|---|---|
| 1 | `0088` | Vibecoding backup target workflow | Add reviewable GitHub-backed sanitized backup publication. |
| 2 | `0089` | Encrypted artifact backup adapter | Add raw artifact backup without making GitHub the dump store. |
| 3 | `0106` | Fresh-checkout recovery drill | Prove the backup strategy works from a clean environment. |

Implementation shape:

- `vibecoding` receives only sanitized bundles and manifests.
- Raw artifacts use encrypted provider-neutral tooling such as `restic`, `borg`, or `rclone`.
- Missing credentials or tools are owner-action blockers, not app failures disguised as success.

Required verification:

```bash
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/
docker compose -f deployment/docker-compose.local.yml run --rm app alembic upgrade head
curl -fsS http://127.0.0.1:8000/health
```

Manual or credential-gated verification:

- Dry-run vibecoding publication with no raw artifacts included.
- Artifact backup command dry-run with credentials absent and present, as available.
- Fresh-checkout restore drill notes under `documentation/uat/`.

STOP:

- Stop when sanitized GitHub backup and encrypted artifact backup are both designed, implemented, and verified through dry runs or documented credential blockers.

## Sprint 3: Rule Applicability And Prompt Safety

Recommended model/reasoning: GPT-5.5 `high`

Tracker issues:

| Order | Issue | Title | Reason |
|---:|---|---|---|
| 1 | `0092` | Rule metadata schema and applicability model | Create the data model for relevance. |
| 2 | `0093` | Rule inventory scanner across harnesses | Discover all guidance surfaces before resolving them. |
| 3 | `0094` | Project-type rule packs | Encode default applicability by project type. |
| 4 | `0095` | Critical rule baseline and fail-closed policy | Prevent critical omissions. |
| 5 | `0096` | Effective rule resolver | Compute the ordered applicable rule set. |
| 6 | `0097` | Prompt coverage linter | Detect missing rules before execution. |
| 7 | `0098` | Prompt and handoff compiler | Generate fresh-session prompts from tracker data. |
| 8 | `0099` | Missing-rule incident workflow | Turn misses into resolver/rule improvements. |
| 9 | `0107` | Rule relevance regression suite | Lock the behavior with fixture projects. |

Implementation shape:

- Build resolver and linter before prompt generation.
- Critical rules should fail closed for implementation prompts and unsafe sync proposals.
- Keep rule contents bounded in MCP outputs; full content is opt-in by ID.

Required verification:

```bash
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/unit/ tests/integration/
docker compose -f deployment/docker-compose.local.yml run --rm app python -m issue_tracker.mcp.server --smoke
docker compose -f deployment/docker-compose.local.yml run --rm app python -m ruff check --no-cache .
```

STOP:

- Stop when fixture projects prove critical rules are included for schema, auth, deployment, MCP, UI provenance, backup, and documentation-only tasks, and irrelevant rules are not forced into low-risk prompts.

## Sprint 4: Cross-Project Sync And Repair

Recommended model/reasoning: GPT-5.5 `high`

Tracker issues:

| Order | Issue | Title | Reason |
|---:|---|---|---|
| 1 | `0100` | Remote GitHub scanner and branch inventory | Move from local checkout scans to real remote branch awareness. |
| 2 | `0101` | Side-by-side rule diff and proposal review | Make repairs reviewable before mutation. |
| 3 | `0104` | Rule version manifests and upgrade notes | Add versioned dependency semantics. |
| 4 | `0102` | PR-based sync execution for rules and backups | Execute approved repairs through PRs. |
| 5 | `0103` | Webhook and polling ingestion | Keep drift current after repo changes. |
| 6 | `0105` | Cross-project sync health dashboard | Show health across all tracked projects. |
| 7 | `0108` | Backup and sync MCP contract expansion | Expose compact agent-facing controls. |

Implementation shape:

- Mock GitHub responses in automated tests; do not require real private tokens.
- Direct push remains disabled except existing explicit mirror workflows.
- PR bodies must include applicability impact, backup impact, verification, and rollback.

Required verification:

```bash
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/
docker compose -f deployment/docker-compose.local.yml run --rm app python -m issue_tracker.mcp.server --smoke
docker compose -f deployment/docker-compose.local.yml run --rm app python -m ruff check --no-cache .
```

Manual or credential-gated verification:

- GitHub scan dry-run against fixture or mocked repos.
- PR creation dry-run or explicit auth-blocked evidence when private credentials are unavailable.
- Browser UAT for cross-project dashboard and proposal review.

STOP:

- Stop when remote scan, proposal review, version manifests, PR execution path, ingestion, dashboard, and MCP tools are implemented with either passing tests or explicit private-repo credential blockers.

## Sequencing Rules

- Do not start PR-based sync execution before the rule resolver and prompt linter exist.
- Do not publish backups to `vibecoding` until the portable bundle schema excludes secrets and raw artifacts by test.
- Do not treat encrypted artifact backup as verified until a restore or metadata verification drill runs.
- Do not close a sprint with only UI evidence; service tests and MCP parity checks are required where applicable.
- Keep markdown and tracker state aligned after each sprint starts or closes.

## Tracker Sprint Creation

Tracker sprint records should be created when each sprint starts, not all at once. The current web/service layer treats every non-closed sprint as active in several views, so pre-creating all four future sprints would make the board misleading.

When starting a sprint:

1. Create the tracker sprint with the matching sprint title.
2. Add only that sprint's issues.
3. Keep issue status and sprint membership aligned.
4. Close the sprint only after all assigned issues pass verification or are explicitly deferred by the user.

## Final Gate

After Sprint 4, run the full release-style gate:

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

## STOP

Sprint 1 is complete. The next action is to start Sprint 2 by creating its tracker sprint record and assigning issues `0088`, `0089`, and `0106`.
