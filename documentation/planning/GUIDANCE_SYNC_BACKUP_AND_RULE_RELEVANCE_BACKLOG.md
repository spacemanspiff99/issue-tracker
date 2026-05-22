# Guidance Sync, Backup, And Rule Relevance Backlog

Date: 2026-05-19

## Context

Issue Tracker already has a first Guidance Sync slice: local guidance source configuration, local checkout scanning, drift classification, dry-run proposals, audit records, deduplicated event ingestion, rollback planning, dashboard, MCP tools, and UAT coverage.

The next product question is broader: how should Issue Tracker keep tracker state recoverable and make sure the right AI rules reach the right GitHub projects and prompts?

## Tracker Intake Check

Before creating this backlog, the active tracker project was queried for voice/audio/intake work using titles and metadata containing `To process`, `voice-feedback`, `audio`, `intake`, or `clarify`.

Result on 2026-05-19:

- Active project: `issue-tracker`.
- Open issues: `0`.
- Matching voice/audio intake issues: `0048`, `0071`, `0074`, `0079`, `0080`, `0081`, `0082`, and `0083`.
- All matching items are already `DONE`. No voice/audio intake item is being deferred from this backlog.

## Tracker Records

This backlog was mirrored into the active tracker project on 2026-05-19.

Sprint execution plan: `documentation/sprints/0109-guidance-sync-backup-rule-relevance-sprint-plan.md`

Oversized overnight execution sprint: `documentation/sprints/0110-overnight-guidance-sync-backup-rule-relevance-completion.md`

| Tracker ID | Phase | Issue |
|---|---|---|
| `0085` | Phase 1 - backup foundation | Backup threat model, recovery objectives, and retention policy |
| `0086` | Phase 1 - backup foundation | Portable recovery bundle schema |
| `0087` | Phase 1 - backup foundation | Export recovery bundle command and UI |
| `0088` | Phase 1 - backup foundation | Vibecoding backup target workflow |
| `0089` | Phase 1 - backup foundation | Encrypted artifact backup adapter |
| `0090` | Phase 1 - backup foundation | Restore verifier and dry-run importer |
| `0091` | Phase 1 - backup foundation | Backup health dashboard and audit trail |
| `0092` | Phase 2 - rule relevance | Rule metadata schema and applicability model |
| `0093` | Phase 2 - rule relevance | Rule inventory scanner across harnesses |
| `0094` | Phase 2 - rule relevance | Project-type rule packs |
| `0095` | Phase 2 - rule relevance | Critical rule baseline and fail-closed policy |
| `0096` | Phase 2 - rule relevance | Effective rule resolver |
| `0097` | Phase 2 - rule relevance | Prompt coverage linter |
| `0098` | Phase 2 - rule relevance | Prompt and handoff compiler |
| `0099` | Phase 2 - rule relevance | Missing-rule incident workflow |
| `0100` | Phase 3 - cross-project sync | Remote GitHub scanner and branch inventory |
| `0101` | Phase 3 - cross-project sync | Side-by-side rule diff and proposal review |
| `0102` | Phase 3 - cross-project sync | PR-based sync execution for rules and backups |
| `0103` | Phase 3 - cross-project sync | Webhook and polling ingestion |
| `0104` | Phase 3 - cross-project sync | Rule version manifests and upgrade notes |
| `0105` | Phase 3 - cross-project sync | Cross-project sync health dashboard |
| `0106` | Phase 4 - recovery drills | Fresh-checkout recovery drill |
| `0107` | Phase 4 - recovery drills | Rule relevance regression suite |
| `0108` | Phase 4 - recovery drills | Backup and sync MCP contract expansion |

## Product Recommendation

Build this as two connected product surfaces:

- `Portable Backup`: recover tracker state, durable markdown, guidance snapshots, and proof of backup health without depending on Issue Tracker-specific internals.
- `Rule Relevance`: make AI guidance behave like a versioned dependency graph with applicability rules, critical-rule gates, prompt coverage checks, and auditable sync proposals.

Use `spacemanspiff99/vibecoding` as the preferred GitHub-backed destination for sanitized, reviewable recovery bundles and guidance manifests. Do not use Git as the only backup mechanism for raw database dumps, audio, screenshots, or large artifacts. Those need an encrypted provider-neutral archive path.

Recommended backup tiers:

- Tier 1: committed durable planning docs and guidance files in normal project repos.
- Tier 2: sanitized portable recovery bundles mirrored to `vibecoding`, using open JSON/Markdown manifests plus checksums.
- Tier 3: encrypted archive backups for raw artifacts and PostgreSQL dumps, stored through a non-app-specific tool such as `restic`, `borg`, or `rclone` to local disk, SFTP, S3-compatible storage, Backblaze B2, GCS, or another replaceable backend.
- Tier 4: recurring restore drills that prove a fresh checkout can recreate the tracker state and guidance status from the backup artifacts.

## Why Critical Rules Were Missed

The earlier prompt workflow likely missed critical rules because `vibecoding` acted like a folder of prompts rather than a rule resolution system.

Failure modes to address:

- Rules did not declare when they apply, which project types need them, or whether they are mandatory.
- Prompt authors had to remember which rule files to include.
- Root guidance, nested overrides, Cursor rules, Codex guidance, command policies, and Claude memory were not compiled into one effective context preview.
- No linter checked that a prompt included every critical rule for the target project, file scope, and task type.
- Rules were copied by path, not by semantic dependency. A prompt could include a broad planning rule while missing a schema, auth, UI provenance, deployment, or MCP safety rule.
- Branch-local guidance could be stale even when the default branch looked current.
- There was no incident loop that turned "rule missed" into a new applicability rule, critical flag, or resolver test.

## Product Principles

- Backup format must be portable. A human should be able to inspect and recover useful state with Git, JSON, Markdown, PostgreSQL tools, and common archive tools.
- GitHub backup should be sanitized. Do not commit secrets, password hashes, sessions, raw audio, database dumps, screenshots, local credentials, or large generated artifacts.
- Rule sync should be review-first. Generate proposals and PRs with evidence before mutating other repositories.
- Rule relevance should be computed. The app should resolve applicable rules from project type, harness, changed files, task type, branch, protected UI provenance, and risk category.
- Critical rules should fail closed. If a prompt or sync proposal omits a critical applicable rule, the UI and MCP should block or warn before execution.
- Every backup and sync action should leave audit evidence and a restore or verification command.

## Backlog

### Phase 1: Backup Foundation

#### Backup threat model, recovery objectives, and retention policy

Recommended model/reasoning: GPT-5.5 `high`

Acceptance criteria:

- Documents what must be recoverable: tracker DB state, durable markdown, guidance files, guidance snapshots, audit events, raw artifacts, and generated exports.
- Defines RPO/RTO targets for local development, weekly project backup, and pre-destructive-reset backup.
- Separates sanitized Git-safe content from encrypted artifact-only backup content.
- Defines retention policy and pruning rules for local, GitHub, and encrypted archive destinations.
- Records why GitHub/vibecoding is not sufficient for raw database dumps or audio artifacts.

#### Portable recovery bundle schema

Recommended model/reasoning: GPT-5.5 `high`

Acceptance criteria:

- Defines an open recovery bundle layout using Markdown, JSON, JSONL, checksums, schema version, project slug, source commit, export timestamp, and tool versions.
- Bundle includes project metadata, issues, sprints, categories, dependencies, issue logs, linked references, guidance source config, guidance snapshots, drift findings, proposals, and audit summaries.
- Bundle excludes secrets, password hashes, sessions, raw audio, screenshots, local certs, `.env`, database dumps, and generated cache files.
- Unit tests prove secret-like fields and ignored artifact paths are excluded.
- Documentation explains how to inspect the bundle without running Issue Tracker.

#### Export recovery bundle command and UI

Recommended model/reasoning: GPT-5.5 `medium`

Acceptance criteria:

- Adds a CLI command to create a portable recovery bundle for one project.
- Adds backup page controls or instructions for creating the bundle.
- Export records source commit, active Alembic revision, app version, timestamp, and checksum manifest.
- Existing JSON export remains supported for compatibility.
- Integration tests cover bundle creation and path safety.

#### Vibecoding backup target workflow

Recommended model/reasoning: GPT-5.5 `high`

Acceptance criteria:

- Adds a configurable backup target path such as `projects/<project>/tracker-backups/latest/` and dated immutable snapshots under `projects/<project>/tracker-backups/snapshots/YYYY-MM-DD/`.
- Writes only sanitized recovery bundles and manifests to `vibecoding`.
- Opens a PR or reviewable commit for backup bundle updates; no raw dumps or local artifacts are committed.
- Includes provenance linking the source repo, source branch, source SHA, tracker project ID, export checksum, actor, and workflow run.
- Fails with a clear blocked status when `VIBECODING_MIRROR_TOKEN` or repository access is unavailable.

#### Encrypted artifact backup adapter

Recommended model/reasoning: GPT-5.5 `high`

Acceptance criteria:

- Defines a provider-neutral artifact backup interface for PostgreSQL dumps, raw audio, screenshots, generated exports, and other ignored artifacts.
- Supports at least one documented backend through common external tooling such as `restic`, `borg`, or `rclone`, without making Issue Tracker the proprietary storage format.
- Stores only encrypted archives outside Git.
- Backup manifests in the tracker link to archive IDs and checksums, not raw secret or artifact contents.
- Verification proves missing tools or credentials fail as owner-action blockers, not silent successes.

#### Restore verifier and dry-run importer

Recommended model/reasoning: GPT-5.5 `high`

Acceptance criteria:

- Validates a recovery bundle before import: schema version, checksum manifest, project identity, categories, dependencies, and migration compatibility.
- Supports dry-run restore that reports what would be created, skipped, merged, or rejected.
- Detects category mapping requirements before mutating data.
- Detects stale bundle schema and recommends the needed migration or export version.
- Tests cover clean restore, duplicate restore, missing category mapping, checksum failure, and unsupported schema.

#### Backup health dashboard and audit trail

Recommended model/reasoning: GPT-5.5 `medium`

Acceptance criteria:

- Project backup page shows last local export, last vibecoding bundle, last encrypted artifact backup, last restore drill, and current health.
- Backup audit entries record command, actor, destination type, checksum, bundle path, result, and next restore command.
- UI distinguishes "never backed up", "stale", "failed", "partial", and "verified".
- MCP exposes compact backup health and next recommended action.
- Browser or route tests verify the backup page remains usable on desktop and mobile.

### Phase 2: Rule Applicability And Critical-Rule Coverage

#### Rule metadata schema and applicability model

Recommended model/reasoning: GPT-5.5 `high`

Acceptance criteria:

- Defines metadata for rules: harness, project types, file globs, task types, risk categories, priority, critical flag, dependencies, conflicts, owner, version, and deprecation status.
- Supports Codex `AGENTS.md`, nested `AGENTS*.md`, `.codex/rules`, Cursor `.mdc`, Cursor skills, Claude memory, and project-specific prompt docs.
- Adds a migration and service tests for rule metadata and applicability queries.
- Documents how a project declares its type and enabled rule packs.
- Backfills metadata for this repository's existing high-priority rules.

#### Rule inventory scanner across harnesses

Recommended model/reasoning: GPT-5.5 `high`

Acceptance criteria:

- Scans configured repositories for all guidance surfaces: `AGENTS.md`, nested `AGENTS*.md`, `.codex/rules`, `.cursor/rules`, `.cursor/skills`, `CLAUDE.md`, prompts, and protected design guidance.
- Extracts metadata, source path, branch, commit SHA, content hash, and provenance.
- Flags missing metadata, duplicate rule IDs, unsupported harnesses, stale mirrors, and generated or secret-like files.
- Includes local checkout tests and mocked remote GitHub tests.
- Does not log private tokens or rule contents in error output.

#### Project-type rule packs

Recommended model/reasoning: GPT-5.5 `medium`

Acceptance criteria:

- Adds rule pack definitions for at least FastAPI/Jinja/PostgreSQL, MCP server, deployment, frontend UI, protected MagicPatterns UI, documentation-only, and generic GitHub project types.
- A project can enable one or more packs and override non-critical defaults.
- The resolver can explain which packs applied and why.
- Tests prove issue-tracker gets FastAPI/Jinja, MCP, deployment, dogfood, and MagicPatterns protection rules when relevant.
- Documentation explains how to add a new project type without editing code paths in multiple places.

#### Critical rule baseline and fail-closed policy

Recommended model/reasoning: GPT-5.5 `high`

Acceptance criteria:

- Defines critical baseline rules that must be present for every Codex implementation prompt in this repo: tracker dogfooding, acceptance criteria, safety boundaries, verification, dirty worktree handling, and closeout evidence.
- Defines additional critical rules by risk: schema/migration, auth/secrets, deployment, MCP contract, UI provenance, backup, and guidance sync.
- Missing critical applicable rules block prompt generation or mark a sync proposal as unsafe.
- UI and MCP return a compact explanation of missing critical rules.
- Tests cover missing baseline, missing schema rule, missing protected UI rule, and missing backup rule.

#### Effective rule resolver

Recommended model/reasoning: GPT-5.5 `high`

Acceptance criteria:

- Given project, branch, harness, task type, changed paths, and risk labels, returns the effective ordered rule set.
- Includes dependency expansion and conflict detection.
- Distinguishes required, recommended, optional, deprecated, and blocked rules.
- Produces a bounded summary plus opt-in full rule content.
- Tests cover overlapping nested guidance, branch stale rules, dependency expansion, and conflict reporting.

#### Prompt coverage linter

Recommended model/reasoning: GPT-5.5 `high`

Acceptance criteria:

- Validates execution prompts against the effective rule set for the target issue or sprint.
- Reports missing critical rules, missing acceptance criteria, missing verification commands, missing STOP handoff, and model/reasoning mismatch.
- Can run from CLI, web route, and MCP.
- Produces a machine-readable result usable by CI.
- Tests cover pass, warn-only, and block states.

#### Prompt and handoff compiler

Recommended model/reasoning: GPT-5.5 `medium`

Acceptance criteria:

- Generates a fresh-session prompt from tracker issue or sprint data.
- Includes context, files in scope, effective rules, acceptance criteria, verification commands, model/reasoning, allowed side effects, evidence rules, and STOP section.
- Shows a preview of included critical rules before export.
- Preserves token discipline by summarizing long guidance and linking exact files.
- Browser or route tests verify generated prompt content for schema, UI, MCP, and backup tasks.

#### Missing-rule incident workflow

Recommended model/reasoning: GPT-5.5 `medium`

Acceptance criteria:

- Adds an incident record type for cases where a prompt missed a critical rule or the wrong rule pack was synced.
- Incident triage can create a rule metadata update, resolver test, or sync proposal.
- Incidents link to tracker issues, prompts, commits, and rule versions.
- Dashboard shows recurring missed-rule patterns.
- Tests prove an incident can update backlog evidence without mutating rules automatically.

### Phase 3: Cross-Project Sync And Repair

#### Remote GitHub scanner and branch inventory

Recommended model/reasoning: GPT-5.5 `high`

Acceptance criteria:

- Scans configured GitHub repositories and branches without requiring local checkouts.
- Handles private repo auth failure, missing branch, rate limit, partial clone/API failure, and protected branch states explicitly.
- Stores remote branch, commit SHA, file metadata, and scan result without logging tokens.
- Can scan `vibecoding` backup/rule targets and child project guidance surfaces.
- Tests use mocked GitHub responses or fixture repos, not real private credentials.

#### Side-by-side rule diff and proposal review

Recommended model/reasoning: GPT-5.5 `medium`

Acceptance criteria:

- Adds proposal detail views with source/target path, source/target branch, source/target SHA, drift type, applicability impact, and side-by-side diff.
- Highlights missing critical rules and protected guidance changes separately from ordinary drift.
- Requires linked tracker issue and verification command before a proposal can move beyond draft.
- Supports copy, delete, rename, merge-needed, skip, investigate, and backup-only actions.
- Browser tests cover desktop and mobile proposal review.

#### PR-based sync execution for rules and backups

Recommended model/reasoning: GPT-5.5 `high`

Acceptance criteria:

- Approved proposals can open PRs against `vibecoding` or child project repositories.
- PR body includes rule applicability impact, backup impact, source and target SHAs, files changed, linked tracker issue, verification checklist, and rollback plan.
- Direct push remains disabled except for explicitly configured mirror workflows.
- Execution records PR URL, branch name, commit SHA, actor, logs, and verification status.
- Failure modes are explicit: auth failure, non-fast-forward, merge conflict, protected branch, rate limit, and unsafe missing critical rule.

#### Webhook and polling ingestion

Recommended model/reasoning: GPT-5.5 `high`

Acceptance criteria:

- Ingests push, PR, and workflow events for configured repos or runs a scheduled polling scan.
- Deduplicates by repo, branch, commit SHA, event type, and path set.
- Triggers drift recomputation and backup health updates when relevant paths change.
- Rejects missing webhook secrets or invalid signatures without leaking payloads.
- Tests cover event ingestion, dedupe, invalid signature, and scan-triggered drift creation.

#### Rule version manifests and upgrade notes

Recommended model/reasoning: GPT-5.5 `medium`

Acceptance criteria:

- Each rule pack has a version manifest with rule IDs, content hashes, dependency graph, changelog, and migration notes.
- Projects can pin a pack version or track latest.
- UI shows available upgrades, breaking guidance changes, and required manual review.
- Sync proposals include version movement and upgrade notes.
- Tests cover pin, upgrade, downgrade warning, and deprecated rule behavior.

#### Cross-project sync health dashboard

Recommended model/reasoning: GPT-5.5 `medium`

Acceptance criteria:

- Shows every tracked project, enabled rule packs, backup status, drift count, missing critical rules, stale branches, and last scan time.
- Filters by project type, harness, severity, owner, branch, and backup health.
- Exports a compact report suitable for a planning note.
- MCP exposes compact cross-project health and next unsafe item.
- Browser UAT proves dashboard is scannable on desktop and mobile.

### Phase 4: Recovery Drills And Quality Gates

#### Fresh-checkout recovery drill

Recommended model/reasoning: GPT-5.5 `high`

Acceptance criteria:

- From a fresh checkout, restore a sanitized recovery bundle into a new database and verify project counts, issue IDs, sprint membership, guidance snapshots, and audit records.
- Verify encrypted artifact backup metadata without restoring raw artifacts by default.
- Record pass/fail notes in `documentation/uat/`.
- Fails clearly if migrations, bundle schema, category mapping, or checksums do not match.
- Adds automated coverage where practical and manual steps where credentials are required.

#### Rule relevance regression suite

Recommended model/reasoning: GPT-5.5 `high`

Acceptance criteria:

- Fixture projects cover multiple project types and task types.
- Tests assert the effective rule resolver includes critical rules for schema, auth, deployment, MCP, UI provenance, backup, and documentation-only tasks.
- Tests assert irrelevant rules are not forced into small low-risk prompts.
- Prompt linter tests fail when known critical rules are removed.
- CI or documented local command runs the suite without private repo credentials.

#### Backup and sync MCP contract expansion

Recommended model/reasoning: GPT-5.5 `high`

Acceptance criteria:

- MCP exposes compact tools for backup health, bundle export planning, restore dry-run summary, rule resolution, prompt linting, and sync next-action summaries.
- Full diffs, full prompts, and full bundle manifests are opt-in by ID and bounded.
- Tools call the same services as the web UI.
- Token discipline tests cover large projects and large drift sets.
- MCP smoke output advertises the new tools.

## Suggested Sequencing

1. Build backup threat model and portable recovery bundle before adding new repository mutation flows.
2. Add rule metadata, inventory scanning, critical baseline, and effective resolver before PR-based sync repair.
3. Add prompt coverage linting before prompt compilation, so generated prompts can prove they contain the required rules.
4. Add remote GitHub scanning and side-by-side proposal review before PR execution.
5. Add recovery drills and rule relevance regression tests before treating the system as reliable.

## STOP

This backlog is ready for issue execution. No implementation should start until the selected issues are assigned to an execution sprint with dependency-aware sequencing and fresh verification commands.
