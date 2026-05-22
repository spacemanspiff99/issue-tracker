# Issue Tracker Product Guide

Issue Tracker is a local-first project tracker for steering AI coding work. It replaces scattered markdown-only backlogs with one FastAPI/Jinja web app, a PostgreSQL database, and a compact MCP server that exposes the same service-layer operations to coding agents.

The product is intentionally not a generic Jira clone. Its main job is to turn rough human input into well-shaped, verifiable implementation work, then preserve enough evidence to close issues and sprints safely.

## Core Concepts

- Project: a repository or work area with its own categories, issues, sprints, releases, and backlog.
- Issue: the canonical unit of work. Issues carry title, status, priority, category, summary, proposed approach, acceptance criteria, planning metadata, dependencies, comments, linked references, and closeout metadata.
- Sprint: a planned execution batch. Sprints share the same four-digit sequence as issues and can contain many issues.
- Release: a metadata-driven rollup across issues and sprints. Release membership comes from the issue milestone field.
- Workflow state: AI handoff state for intake, clarify, ready-for-codex, implementing, verifying, and closed.
- Category: project-scoped taxonomy and prevention checklist. Tracker categories are not hardcoded from other projects.

## Web UI Functionality

- First-run setup and login create and protect the local admin account.
- Project list supports search, project creation, and non-destructive archive/restore for UAT, restored, or imported project clutter.
- Project overview shows issue totals, done percent, blocked count, uncategorized count, AI workflow counts, release readiness, voice intake entrypoint, saved views, quick issue creation, issue table actions, sprint creation, sprint progress, categories, recent activity, and issue log entries.
- Saved issue views filter by all, backlog, active sprint, blocked, done, and uncategorized. Issue search covers title, summary, category, and acceptance criteria.
- Backlog view supports drag-and-drop ordering and a route-backed Save order form.
- Board view is sprint-oriented. It defaults to the active sprint when one exists, supports single-sprint and multi-sprint filtering, can show all work, and includes backlog-to-sprint assignment controls.
- Release view rolls up issues by milestone, showing progress, blockers, unscheduled work, linked sprints, and readiness notes from `readiness=...` custom fields.
- Intake view supports voice feedback. Users can record audio in the browser, upload an audio file, add written notes, mark ambiguous feedback as Not Done / Needs Clarifications, and create a backlog intake issue.
- Issue detail provides editing, workflow state changes, sprint assignment, planning metadata, acceptance criteria, dependencies, notes timeline, GitHub/reference links, closeout metadata, and a responsive sidebar for fast context.
- Sprint detail shows sprint context, rollup progress, issue membership, backlog assignment, and close action.
- Planning and backup pages point to durable markdown and CLI workflows without committing generated exports or backups.
- Guidance Sync shows configured guidance sources, tracked paths, scan health, drift findings, sync proposals, and audit evidence for cross-repository AI guidance alignment.

## Voice Feedback Workflow

Voice feedback is intake-first and provider-neutral.

1. Open a project and select Intake, or use Open audio intake from the project overview.
2. Enter a short title.
3. Either record audio in the browser or upload an audio file.
4. Add optional written notes or a transcript.
5. Check Not Done / Needs Clarifications when the report is ambiguous.
6. Submit the form to create a normal backlog issue labeled as voice feedback.

Uploaded or recorded audio is stored under the ignored local artifact path `exports/voice-feedback/`. Raw audio must not be committed. The created issue stores a local artifact reference, written notes, acceptance criteria for Codex processing, and workflow metadata. The next step is for Codex or a human to investigate the intake and convert it into a build-ready issue or leave it in `clarify`.

## Agent And MCP Functionality

The stdio MCP server uses the same service layer as the web UI. It exposes compact tools for project listing, issue creation, issue lookup, issue search, status updates, dependencies, sprint creation, sprint assignment, sprint lookup, category listing, and next-action summaries.

Guidance Sync MCP tools expose compact sync health, drift listing, and proposal creation. Full diff or repository mutation workflows are intentionally not default MCP output.

MCP responses should stay compact by default. Full issue text, acceptance criteria, and history are opt-in by ID.

## Guidance Sync Workflow

Guidance Sync is the product area for keeping AI guidance aligned across project repositories and the shared `spacemanspiff99/vibecoding` registry.

Current implemented scope:

- Configure project guidance sources with repo URL, default branch, vibecoding target path, and tracked guidance paths.
- Scan local repository checkouts for tracked guidance files while excluding generated artifacts, backups, exports, caches, and obvious key/certificate files.
- Record branch and file snapshots with commit SHA, file path, content hash, size, scan status, actor, and timestamp.
- Classify drift as in-sync, stale, local-only, target-only, renamed, protected-change, auth-blocked, or scan-incomplete.
- Create idempotent sync proposals that require a linked tracker issue and verification command before execution.
- Require explicit approval text before protected guidance proposals can move to ready.
- Execute proposal dry runs, generate PR body text, record audit events, ingest deduplicated push-style events, and generate rollback plans.

Planned next maturity level:

- Fetch and compare remote GitHub branches without requiring local checkouts.
- Show richer side-by-side file diffs and branch matrices.
- Open PRs against vibecoding or child project branches from approved proposals.
- Add webhook or polling ingestion wired to real repository events.

## Data And Safety

- PostgreSQL is the normal durable runtime database.
- Alembic migrations live in the root `migrations/` tree.
- JSON import/export commands are available for project data, with explicit category mapping required when source categories exist.
- Exports, backups, screenshots, raw audio, local databases, credentials, and other generated artifacts are ignored by git.
- Closing issues preserves close metadata: originating LLM, closed by, close note, and closed timestamp.
- Closed issue metadata is immutable through the service layer.

## Verification

The expected local verification path is Docker-based:

```bash
docker compose -f deployment/docker-compose.local.yml config
docker compose -f deployment/docker-compose.local.yml build
docker compose -f deployment/docker-compose.local.yml run --rm app alembic upgrade head
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/
docker compose -f deployment/docker-compose.local.yml up -d
curl -fsS http://localhost:8000/health
docker compose -f deployment/docker-compose.local.yml exec -u root app env RUN_BROWSER_UAT=1 python -m pytest tests/e2e/
docker compose -f deployment/docker-compose.local.yml run --rm app python -m issue_tracker.mcp.server --smoke
docker compose -f deployment/docker-compose.local.yml run --rm app python -m ruff check --no-cache .
```
