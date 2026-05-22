# Vibecoding Rule Sync Product Plan

Date: 2026-05-15

Status update: Sprint `0084` implemented the first local Guidance Sync slice. The schema, service, web dashboard, compact MCP tools, audit records, deduplicated event ingestion, dry-run proposal execution, rollback planning, and UAT coverage now exist in this repository. Remote GitHub branch scanning, side-by-side diff review, webhook or polling automation, and real PR creation remain planned follow-on work.

Expanded backlog: `documentation/planning/GUIDANCE_SYNC_BACKUP_AND_RULE_RELEVANCE_BACKLOG.md` adds portable backup strategy, vibecoding backup targets, rule applicability metadata, critical-rule coverage, prompt linting, and cross-project sync repair work.

## Investigation Scope

The goal is to make Issue Tracker the interface for projects that use `spacemanspiff99/vibecoding` as a shared guidance/rules repository, with enough branch awareness to prevent rule changes from getting lost or drifting out of sync.

Direct repository access note: this environment does not have a local `vibecoding` checkout, and unauthenticated GitHub API requests for `spacemanspiff99/vibecoding` returned `404`. This plan is based on the existing mirror workflow in this repository, existing planning references to `vibecoding`, and the current Issue Tracker product shape.

## Current State

Issue Tracker currently has a GitHub Actions workflow, `.github/workflows/mirror-rules.yml`, that:

- Runs on pushes to `main` when guidance files change.
- Checks out this source repo and the private `spacemanspiff99/vibecoding` repo using `VIBECODING_MIRROR_TOKEN`.
- Copies `.cursor/rules`, `.cursor/skills`, `AGENTS.md`, nested `AGENTS*.md`, `.codex/rules`, and `CLAUDE.md`.
- Writes `.mirror-source.json` containing project, source repo, source branch, source SHA, actor, run ID, and mirror timestamp.
- Commits mirrored content into `vibecoding` under `projects/issue-tracker/...`.
- Pushes only to `vibecoding` `main`, with retry/rebase handling.

This is a good publishing mechanism, but it is not yet a product workflow. It does not track child project branches, detect drift, show sync status, open repair PRs, or protect user-edited branch-local guidance from being overwritten.

## Product Goal

Issue Tracker should become the control plane for AI guidance across local project repos and the `vibecoding` registry:

- Show every tracked project and its source rule locations.
- Show every relevant branch in each child project.
- Compare local project rules, mirrored vibecoding rules, and branch-local rule variants.
- Detect stale, missing, divergent, deleted, renamed, and manually edited guidance.
- Recommend safe sync actions.
- Create auditable sync proposals instead of silently overwriting branch work.
- Preserve provenance for every mirror and every repair.

## Recommended Product Model

Add a new "Guidance Sync" area to Issue Tracker.

Core entities:

- `GuidanceSource`: a project repository plus the canonical guidance paths to scan.
- `GuidanceTarget`: a vibecoding path such as `projects/<project>/cursor-rules`.
- `GuidanceBranch`: a branch in either the source repo or vibecoding repo.
- `GuidanceFile`: normalized metadata for each tracked guidance file.
- `GuidanceSnapshot`: file hashes, source SHA, branch, timestamp, actor, and workflow run evidence.
- `GuidanceDrift`: comparison result between two snapshots.
- `GuidanceSyncProposal`: planned copy, delete, rename, merge, or no-op actions.
- `GuidanceSyncRun`: executed sync result, logs, commit SHAs, PR URLs, and verification status.

The first implemented slice is read-mostly: it can record scans, classify drift, create proposals, record audit events, ingest deduplicated events, and execute dry-run proposal flows. Actual writes to child repos or vibecoding should still come later through explicit PR workflows.

## Branch Drift Risks To Handle

The main risk is not just "rules changed"; it is "rules changed in one branch or mirror and no one noticed." Specific failure modes:

- Child project feature branches continue using stale rules after `main` updates.
- A branch changes rules locally and later receives a mirror overwrite from `main`.
- Vibecoding `main` receives a mirror from one project while another project's branch references older shared guidance.
- Rules are renamed or split, causing stale files to remain in branch-local folders.
- Deleted rules keep existing in mirror destinations because deletion intent is not distinguished from missing files.
- Two agents change the same rule in different branches and both appear valid.
- MagicPatterns or other protected UI guidance is modified by accident.
- `.cursor`, `AGENTS.md`, `.codex`, and `CLAUDE.md` drift independently.
- Mirror provenance points to a source SHA that is no longer reachable from the branch expected by a child project.
- A branch has unmerged guidance changes with no issue, acceptance criteria, or closeout evidence.
- Private repo auth failures are misread as "no drift".
- GitHub API rate limits or partial clone failures create incomplete scans.
- Generated artifacts, secrets, or local files accidentally enter a sync proposal.
- Workflow push races create non-fast-forward retries that hide semantic conflicts.
- Manual edits in vibecoding are overwritten without review.
- Child projects use different branch strategies, so assuming `main` everywhere misses active branches.
- Subdirectories or nested `AGENTS.override.md` files override root guidance and are not compared.

## Sync Strategy

Use a conservative, review-first model.

1. Inventory
   Discover projects, repos, default branches, guidance paths, and vibecoding target paths.

2. Snapshot
   Capture branch-specific file lists and hashes for source and vibecoding paths. Store source commit, branch, author, and timestamp.

3. Compare
   Compare canonical source to target mirror, default branch to active child branches, and root guidance to nested overrides.

4. Classify
   Classify results as in-sync, stale, local-only, target-only, renamed, deleted, conflict, protected-change, auth-blocked, or scan-incomplete.

5. Plan
   Create a sync proposal with exact file actions and risk labels. Do not write yet.

6. Review
   Surface proposal in the UI with file-level diffs, provenance, and linked tracker issues.

7. Execute
   Later phase: open PRs against source child repos or vibecoding, never silent direct pushes except for already-approved mirror workflows.

8. Verify
   Re-scan after merge and attach evidence to the tracker issue.

## UI Shape

Guidance Sync dashboard:

- Project list with sync health.
- Branch matrix by project: default branch, active feature branches, last scanned SHA, drift count.
- Harness tabs: Cursor rules, Cursor skills, Codex guidance, Codex command policy, Claude memory.
- Drift queue with severity, owner, file path, branch, source SHA, target SHA, and recommended action.
- Proposal detail with side-by-side diff, provenance, affected branches, protected guidance warnings, and create-issue/open-PR actions.
- Audit page with previous sync runs, PR links, workflow run links, and verification commands.

## Backlog Issues

The following backlog issues should be created in the tracker.

### Issue 0056: Model guidance sources, targets, branches, snapshots, and drift

Recommended model: GPT-5.5 high

Acceptance criteria:

- Schema represents guidance sources, targets, branches, files, snapshots, drift findings, proposals, and sync runs.
- Snapshot records include repo, branch, commit SHA, path, content hash, actor if known, scan timestamp, and scan status.
- Drift findings distinguish stale, local-only, target-only, deleted, renamed, conflict, protected-change, auth-blocked, and scan-incomplete.
- Alembic upgrade works on an empty database.
- Unit tests cover branch-aware drift classification.

### Issue 0057: Add repository inventory and auth-safe scanning

Recommended model: GPT-5.5 high

Acceptance criteria:

- Project settings can store source repo URL, default branch, vibecoding target path, and tracked guidance paths.
- Scanner can list branches and fetch guidance files without logging tokens.
- Private repo auth failures are represented as blocked scan results, not as empty success.
- Scanner excludes generated artifacts, secrets, exports, backups, and ignored local artifacts.
- Route or service tests cover successful scan, missing auth, and partial scan behavior.

### Issue 0058: Build branch-aware drift detection service

Recommended model: GPT-5.5 high

Acceptance criteria:

- Service compares default branch to child branches and source guidance to vibecoding mirrors.
- File-level hashes and normalized paths are used for detection.
- Renames and deletions are classified separately from simple missing files.
- Nested `AGENTS.override.md` and harness-specific paths are included.
- Tests cover stale branch, branch-local edit, mirror-only file, deleted file, renamed file, and protected MagicPatterns change.

### Issue 0059: Add Guidance Sync dashboard

Recommended model: GPT-5.5 medium

Acceptance criteria:

- Project detail links to a Guidance Sync page.
- Dashboard shows project sync health, branch matrix, scan status, and drift count.
- Harness tabs separate Cursor, Codex, Claude, and command-policy guidance.
- Drilldown shows file path, source branch/SHA, target branch/SHA, drift classification, and recommended action.
- Mobile route-level or browser verification proves the dashboard does not overflow.

### Issue 0060: Create sync proposal workflow

Recommended model: GPT-5.5 high

Acceptance criteria:

- A drift finding can create a sync proposal without mutating any repository.
- Proposal records exact actions: copy, delete, rename, merge-needed, skip, or investigate.
- Proposal requires linked issue, acceptance criteria, owner, and verification command before execution.
- Protected MagicPatterns guidance requires explicit user approval text before proposal can move beyond draft.
- Tests prove proposal creation is idempotent and auditable.

### Issue 0061: Add PR-based sync execution

Recommended model: GPT-5.5 high

Acceptance criteria:

- Approved proposal can open a PR against vibecoding or a child project branch.
- Direct pushes are not used for branch repair unless a project setting explicitly allows it.
- PR body includes source/target SHAs, files changed, drift reasons, linked tracker issue, and verification checklist.
- Execution stores PR URL, branch name, commit SHA, and run logs.
- Failure modes include auth failure, non-fast-forward, merge conflict, protected branch, and rate limit.

### Issue 0062: Add GitHub webhook or polling ingestion

Recommended model: GPT-5.5 high

Acceptance criteria:

- App can ingest push/workflow events or run a polling scan for configured repos.
- Relevant guidance changes automatically create or update drift findings.
- Events are deduplicated by repo, branch, commit SHA, and path set.
- Missing webhook secrets or invalid signatures are rejected without leaking payloads.
- Tests cover event ingestion, dedupe, and rejected signatures.

### Issue 0063: Add sync audit log and rollback planning

Recommended model: GPT-5.5 high

Acceptance criteria:

- Every scan, proposal, execution, and verification creates immutable audit entries.
- Audit entries link to workflow runs, PRs, commits, actors, and tracker issues.
- Rollback plan can be generated for an executed sync without automatically reverting.
- UI shows what changed, why, and how to recover.
- Tests cover audit immutability and rollback-plan generation.

### Issue 0064: Add MCP tools for guidance sync

Recommended model: GPT-5.5 high

Acceptance criteria:

- MCP exposes compact tools to list sync health, scan a project, inspect drift by ID, create proposal, and summarize next actions.
- Full diffs are opt-in by ID and bounded in size.
- MCP tools call the same guidance sync service as the web UI.
- Token discipline tests cover large drift sets.
- Tool smoke output includes guidance sync capabilities.

### Issue 0065: Add containerized UAT for rule sync workflows

Recommended model: GPT-5.5 high

Acceptance criteria:

- Docker-based tests cover project setup, guidance source configuration, scan, drift display, proposal creation, and audit evidence.
- Browser UAT covers desktop and mobile Guidance Sync pages.
- Tests use local fixture repositories or mocked GitHub API responses, not real private tokens.
- `/health` remains database-backed.
- UAT notes record pass/fail evidence and blocked private-repo checks separately.

## Recommended Phasing

Phase 1: Read-only foundation

- Issue 0056
- Issue 0057
- Issue 0058
- Issue 0059

Phase 2: Safe planning and review

- Issue 0060
- Issue 0063
- Issue 0064

Phase 3: Controlled execution

- Issue 0061
- Issue 0062
- Issue 0065

Do not build PR-writing or webhook execution before read-only branch drift detection is reliable. The product is most valuable when it can say, with evidence, exactly where rules are stale or divergent before it tries to repair anything.
