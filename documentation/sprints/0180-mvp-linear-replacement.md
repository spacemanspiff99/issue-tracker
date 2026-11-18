# Sprint Plan: MVP, Replace Linear For Owner Projects

Status: active. Tracker sprint `0180` (created 2026-11-17) holds issues `0181`–`0204` plus `0176`, `0144`, `0145`, `0152`. IDs match this plan. `0195` is the test-isolation follow-up, and `0204` is the ADR.

Created: 2026-11-17

Recommended model/reasoning: `deep` (Claude Opus at high effort, GPT-5.5 `high`). The work touches tracker state integrity, MCP contracts, backups, and deployment.

## MVP Definition (owner, 2026-11-17)

MVP means this tracker replaces Linear as the working backlog for the owner's other projects (weather-app, matterhub, relay67, and others).

- **Runtime:** the live tracker is the instance on the dev host (`192.168.10.20:8000`), served as `dev.it.462111.xyz`. k3s production (`0178`) is post-MVP.
- **Linear data migration is post-MVP.** It happens after the MVP gate passes and the owner says the tracker is ready to migrate.
- **Backlog triage is in scope** (Phase B).

This replaces the scope in `documentation/planning/MVP_SCOPE_LOCK.md`, which records the original single-user build.

## Consequences Of Running On The Dev Host

The dev database (`issue-tracker-postgres`, volume `issue_tracker_pgdata`) becomes the durable source of truth. Treat it like production from Phase A onward:

- Take a verified backup before any destructive tracker change.
- Run scheduled backups, keep a copy off the host, and prove a restore works.
- Never point tests or `TEST_DATABASE_URL` at it. Run preflight in isolated compose projects only.
- Rebuilding the live app from a dirty working tree is a deploy. Phase C decides how the live instance is pinned to a known SHA.

## Issues

| Order | ID | Phase | Priority | Issue |
|---:|---|---|---|---|
| 1 | `0181` | A. Integrity | urgent | Fix MCP integer argument coercion on PostgreSQL and add PostgreSQL-backed MCP tests |
| 2 | `0182` | A. Integrity | urgent | Verified backup of the live dev database before triage |
| 3 | `0183` | B. Triage | urgent | Remove Browser UAT test projects and junk issues |
| 4 | `0184` | B. Triage | urgent | Resolve stale sprints `0119`, `0140`, `0168` and the `0154` redesign backlog |
| 5 | `0185` | C. Durable runtime | urgent | Pin the live instance to a known SHA and add a restart policy |
| 6 | `0186` | C. Durable runtime | urgent | Scheduled backups with an off-host copy and a restore drill |
| 7 | `0176` | C. Durable runtime | high | HTTPS for `dev.it.462111.xyz` (Caddy + AdGuard), existing issue |
| 8 | `0204`, `0187`, `0190`–`0200` | D. Linear-compatible API | urgent | ADR, keys, team/state model, labels, comments, relations, milestones, uploads, `/graphql` subset, endpoint overrides, GitHub automation, MCP compat |
| 9 | `0188` | E. Owner UI parity | high | Issue detail, board, and filters for the new fields; per-repo projects |
| 10 | `0189` | F. MVP gate | urgent | Pilot with one repo, run the full gate, record the MVP decision |

## Phase A: Tracker Integrity

### `0181` Fix MCP argument coercion

Evidence (2026-11-17): `next_action`, `sprint.get`, and `issue.search` fail with `operator does not exist: integer = character varying`. The cause is in `src/issue_tracker/mcp/server.py`, where the tools are registered as lambdas with no type hints. FastMCP then types every argument as a string, so `"1"` reaches SQLAlchemy as `VARCHAR`. The tests run on SQLite, which accepts that comparison, so they never caught it.

Acceptance criteria:

- [x] Every MCP tool declares typed parameters (int IDs, bool flags, int limits). The published tool schema shows `integer`/`boolean` where appropriate.
- [ ] A test calls each read tool and each mutation tool through the FastMCP layer, with no direct `tools.*` calls, against PostgreSQL in an isolated compose project. It fails on the current code and passes after the fix. Partial (2026-11-17): a FastMCP-layer regression test asserts integer/boolean schemas and string-ID coercion. It fails before the fix and passes after, on SQLite. The PostgreSQL run is blocked by the `guard-destructive.sh` hook, which treats any PostgreSQL `TEST_DATABASE_URL` as a real tracker database. The owner must decide on a guard exception for throwaway compose databases.
- [x] `project.list`, `next_action`, `sprint.get`, `issue.search`, and `issue.get` succeed against the live dev database from this Claude Code session.
- [ ] `IT-4` checklist passes. Compact summaries stay the default.

### `0182` Pre-triage backup (dropped)

The owner says on 2026-11-17 that the dev database holds nothing worth keeping, so no ticket. A plain `pg_dump` runs before deletions only as a free safety net.

- [ ] A `pg_dump -Fc` of the live database exists under `backups/` (git-ignored), is non-empty, and `pg_restore --list` reads it.
- [ ] A test restore into a throwaway database shows the row counts for projects, issues, and sprints match the live database.

## Phase B: Backlog Triage

Triage changes tracker state in a destructive way. It runs only after `0182` passes. Deleting projects needs a service-layer operation (or a reviewed one-off command) that removes dependent rows in the correct order, not ad hoc SQL.

### `0183` Remove test data

- [ ] All `Browser UAT Project *` projects (ids 3–22 as of 2026-11-17) and `Manual-UAT-Restored` (id 2) are removed, along with their issues, sprints, categories, and logs. Project `issue-tracker` (id 1) row counts are unchanged.
- [ ] `0153` (`test1`) is closed as invalid, with close metadata.
- [ ] Browser UAT tests no longer leave projects in the live database. They run only against isolated databases.

### `0184` Resolve stale sprints

Dispositions below were accepted by the owner on 2026-11-17 ("just get to MVP").

| Sprint | Issues | Proposal |
|---|---|---|
| `0119` production-readiness drill | `0122`–`0128` | Close the sprint. Defer all to post-MVP `0178` (k3s), because the dev-host decision supersedes them. Phases C and F re-cover backup, restore, and UAT evidence for MVP. |
| `0140` usability rescue | `0143`–`0145`, `0147`–`0149`, `0151`, `0152` | Check each against the current UI. Close the ones already done, with evidence. Move the open ones that affect daily use (`0144`, `0145`, `0152`) to Phase E. Defer the rest. |
| `0168` UAT deploy and validation | `0173`–`0175` | Close the sprint. Phase F's gate replaces it. |
| `0154` AI workflow redesign (no sprint) | `0154`–`0167` | Defer as post-MVP, except items the owner names as Linear-parity needs in `0188`. |
| Other backlog | `0176`, `0178`, `0179` | `0176` moves into Phase C. `0178` and `0179` are post-MVP. |

Acceptance criteria:

- [x] The owner accepts or amends the table above (accepted 2026-11-17).
- [ ] After that, only this sprint is active. Every open issue is in this sprint or is explicitly deferred with a note.
- [ ] Voice and audio intake items in project 1 are checked and processed or deferred (none found outside test projects on 2026-11-17).

## Phase C: Durable Runtime On The Dev Host

### `0185` Pinned live instance

Recommendation: run the live tracker as a SHA-pinned stack built from `git archive <sha>`, reusing the guards in `local-uat-deploy.sh`. Keep the existing volume (no data move) and the `restart: unless-stopped` change now in the working tree. Do day-to-day development in a separate compose project on another port, so editing code never changes the live tracker.

- [ ] The live instance reports its deployed SHA (for example on `/health` or in a recorded deploy log), and the deploy refuses dirty or unpushed SHAs.
- [ ] A dev stack can run tests and preflight without touching `issue_tracker_pgdata` or port `8000`.
- [ ] The live stack survives a host reboot, and `/health` shows the database ok afterwards.
- [ ] `IT-6` checklist passes.

### `0186` Backups and restore

- [ ] A daily `pg_dump -Fc` runs on a schedule (host cron or a compose service), with retention.
- [ ] A copy leaves the host. Decision (2026-11-18, owner): the owner's Kopia backup server snapshots `backups/` off-host. B2 is dropped. The Kopia session has the request, and `0186` stays open until a Kopia snapshot exists and its restore path is documented.
- [ ] A restore drill into a throwaway database is recorded in `documentation/uat/`.
- [ ] `IT-5` checklist passes. Backup credentials are not committed.

### `0176` HTTPS

- [ ] `https://dev.it.462111.xyz/health` returns the database ok from a LAN client, `SESSION_COOKIE_SECURE=true`, and `APP_BASE_URL` matches.

## Linear Usage Interviews (2026-11-17)

Answers from the project sessions `dev1.planwx-7-MASTER-05` (weather-app), `dev.relay67.com` (relay67/daycare-messaging), and `dev.matterhub-r1.1--02` (matterhub/legal-project-management), taken from each repo's rules, skills, and scripts:

- **Access path:** all three use Python GraphQL scripts with an API key from env (`~/vibecoding/scripts/linear.py`, wrapped per repo, or relay67's own `scripts/prompts/relay67/*.py`). The Linear MCP is only a fallback. Repos run on other hosts (dev1 `.22`, dev2 `.21`, dev3 `.24`, LXCs `dev` and `legal-dev`), so **a token-authenticated HTTP API is the primary interface**. MCP is nice-to-have.
- **Operations:** create, get, filtered list (project, state, priority, label, parent, milestone, updated-since, limit, fields/json), update (state, title, description, priority, labels, parent), comment, list comments, list states, list labels, and create labels.
- **Workflow states:** a custom set per project, with types: Pending (backlog), Planned (unstarted), In Progress, In Review, Merged, UAT (started), Done (completed), Canceled, Duplicate. Scripts test the state *type*, not just the name.
- **Fields:** priority P1–P4 (strict); labels (load-bearing for release and lane scoping, e.g. `release-7.1`, `lpm-rN`, `owner-action`); project scoping (WEA team spans several products); markdown descriptions; parent/sub-issues (weather-app, matterhub); `blocks` relations (relay67 reconciler, weather-app); project milestones per release (relay67). Unused: cycles, estimates, due dates, mostly assignee.
- **Comments are critical** and mostly written by agents, tagged `[S-<host>-<id8>]`. Continuation prompts are read as "comment id X and everything after it", or as the latest N. Required: stable comment ids, author, created-at, chronological order, `after=<id>` and `latest=N` reads.
- **GitHub automation** (must-have for weather-app and matterhub): a `wea-###` token in the branch name plus a non-draft PR moves the issue to In Progress, then In Review. `Refs` is used instead of auto-close, and the move to Merged happens by script.
- **Attachments:** must-have for weather-app (evidence images), nice-to-have for matterhub.
- **Identifiers:** `WEA-n` ids appear throughout code, commits, branches, and docs, so imported issues must keep a resolvable alias.
- **Constraint (matterhub):** case material never goes into the tracker.
- **Owner views:** no repo evidence. The owner follows issue and comment links, and likely reads on mobile.

## Phase D: Linear-Compatible API

### Design decision (2026-11-17, from the traces)

The weather-app trace (`scripts/linear.py`) and the relay67 trace (its own scripts) both send Linear GraphQL directly, with a raw key in `Authorization`. relay67 also calls the claude.ai Linear MCP tools (`get_issue`, `list_issues`, `list_comments`, `save_comment`, `save_issue`, `list_milestones`, `save_milestone`). So:

- **Serve a Linear-compatible GraphQL subset at `/graphql`.** It covers exactly the queries and mutations in `tests/fixtures/linear_traces/*.jsonl`, with the same field names, connection shape (`nodes`, `pageInfo{hasNextPage endCursor}`), filters, error envelope, and `Authorization: <key>` header. The consuming scripts change only their endpoint and key (a `LINEAR_API_URL` env override). No new REST API or CLI to port to.
- **Model Linear's shape:** a **team** (key `WEA`) owns typed workflow states, labels, and a team-wide identifier sequence. **Projects** (weather-app, relay67, matterhub, ...) belong to the team. Issues keep `WEA-n` identifiers, and the post-MVP migration imports them with their existing numbers, so ids in code, commits, and branches stay valid. This tracker's own project keeps its `NNNN` display convention, as a separate team.
- **Mirror the Linear MCP tool names** in a compat tool set, so agents that use the Linear MCP switch servers without changing prompts.
- Every resolver calls the shared service layer. Web, GraphQL, and MCP never duplicate lifecycle logic.

This is a `deep` architecture change touching schema, auth, and the API contract. Write it as an ADR in `documentation/architecture/` and have it Opus-reviewed before `0190` starts.

| ID | Issue | Tier |
|---|---|---|
| `0204` | ADR: Linear-compatible team/project/state/identifier model and GraphQL subset, scoped from the trace fixtures | deep |
| `0187` | API keys: per-team keys, hashed at rest, created and revoked in the web UI, sent as `Authorization: <key>` (`IT-5`) | deep |
| `0190` | Schema: teams, typed workflow states with position, team-wide identifier sequence, project to team, issue `sortOrder`, priority 0–4. Migration plus backfill keeps the existing tracker project working (`IT-1`, `IT-3`) | deep |
| `0191` | Labels (team-scoped, color, description, create), markdown descriptions, parent/sub-issues | standard |
| `0192` | Comments: append-only plus edit (MCP `save_comment` with id), stable ids, author or bot actor, createdAt, url, chronological and cursor pagination (`IT-1`) | deep |
| `0193` | Relations `blocks`, `related`, `duplicate`, with `relations`/`inverseRelations`, create/delete, and duplicate-create rejection | standard |
| `0194` | Project milestones (create, list, issue assignment, filter by name). Initiatives are minimal (create, list, link a project) | standard |
| `0196` | File upload (`fileUpload`, then PUT to `uploadUrl`, then `assetUrl`) and `attachmentCreate`, stored on the data volume and included in backups (`IT-5`, `IT-6`) | standard |
| `0197` | `/graphql` endpoint implementing every query and mutation shape in the fixtures, with filters (`title.startsWith`, `project.id.eq`, `projectMilestone.name.eq`, state, label, parent, updatedAt), `orderBy`, and pagination (`IT-4`) | deep |
| `0198` | `LINEAR_API_URL` override PRs for `vibecoding/scripts/linear.py` (through the mirror workflow) and relay67's scripts. Each repo session makes the change in its own repo | standard |
| `0199` | GitHub branch-token automation: a dev-host poller (outbound `gh` API only) moves `wea-###` issues to In Progress on branch push and In Review on a non-draft PR, with per-project branch rules | deep |
| `0200` | MCP compat tools with Linear MCP names over the same services | deep |

Acceptance criteria (phase):

- [ ] Every GraphQL operation in the fixtures runs against an isolated stack and returns every field listed in its `reads` (`0202`).
- [ ] `linear.py` (all subcommands in the weather-app trace) and relay67's scripts run unmodified apart from the endpoint override.
- [ ] A key for team A cannot read or write team B (test).
- [ ] The branch automation moves states within one poll interval.
- [ ] Web, GraphQL, and MCP all call the same service operations (tests).

## Phase E: Owner-Facing UI Parity

### `0188` Owner views

- [ ] Issue detail shows the markdown description, comments timeline, attachments, relations, sub-issues, and labels, and is usable at phone width (browser check).
- [ ] The board groups by the project's workflow states, and the list filters by state, label, priority, and milestone.
- [ ] The `0140` carry-overs `0144`, `0145`, `0152` are checked, and closed or done.
- [ ] Projects exist for weather-app, matterhub, and relay67, with their state sets and labels, and empty backlogs until migration.

## Phase F0: Linear Operation Conformance (Required For MVP)

The owner requires every Linear operation the consuming repos actually perform to be replayed end to end before MVP is declared done.

| ID | Issue | Tier |
|---|---|---|
| `0201` | Capture sanitized JSONL operation traces from each project session's transcripts, scripts, and workflows. Store them as fixtures under `tests/fixtures/linear_traces/<repo>.jsonl` (placeholders only, no secrets, no case material) | standard |
| `0202` | Trace replay harness: for each trace line (and each multi-step `flow`), run the recorded GraphQL operation, or the real `linear.py` subcommand, against an isolated compose stack and assert the effect plus every field in `reads`. Runs in the Docker test gate | deep |
| `0203` | Live acceptance in each repo: its session runs its real workflow through the CLI against the live instance in a scratch project. Create, branch, PR to In Review, comment handoff, the successor reads after id, Merged, Done, plus relations, labels, milestones, and attachments as each repo uses them. Record the evidence in `documentation/uat/` | deep |

Trace line format (sent to the sessions 2026-11-17): `repo`, `source`, `op`, `argv` or `graphql`, `inputs`, `reads`, `expect`, `count`, and an optional `flow`.

Acceptance criteria:

- [ ] Trace fixtures received for weather-app (49 lines, received), relay67 (57 lines, received), and matterhub (pending), or the owner waives a repo explicitly.
- [ ] Every distinct `op` and `flow` in the fixtures has a passing replay test. Unsupported ops fail the gate and cannot be silently skipped.
- [ ] Each repo session reports a passing live acceptance run.

## Phase F: MVP Gate

### `0189` Pilot and decision

- [ ] `0202` replay suite and `0203` live acceptance pass for every repo.
- [ ] Run `/local-uat-preflight` in full on the release SHA: fresh build, migration on an empty database, pytest, browser UAT, and MCP smoke.
- [ ] Deploy the SHA to the live instance (`0185`). A backup is taken first, and `/health` shows the database ok.
- [ ] One pilot repo (recommended: relay67, which has the smallest automation surface and no GitHub-token dependency; weather-app goes second) runs its agent work through the tracker for at least one real sprint with no Linear fallback. Record the friction it hits as issues.
- [ ] Record the owner's MVP decision in `documentation/uat/`.

## Out Of Scope (Post-MVP)

- Importing Linear data into the weather-app, matterhub, and relay67 projects (the next sprint after MVP).
- k3s production (`0178`), mcp 2.x port (`0179`), networked MCP, and the AI workflow redesign (`0154` plan), unless pulled in by `0188`.

## Verification

```bash
DC="docker compose -f deployment/docker-compose.local.yml"
$DC run --rm app python -m pytest tests/
$DC run --rm app ruff check src tests
$DC run --rm app python -m issue_tracker.mcp.server --smoke
curl -fsS http://192.168.10.20:8000/health
curl -fsS https://dev.it.462111.xyz/health
```

## STOP

Progress as of 2026-11-17:

- `0181` done: PR #36 merged into `dev` (`c44c20f`). Opus review PASS, twice.
- PostgreSQL test support: PR #37 merged into `dev` (`2879038`). The `postgres-test` service plus a `_test` name guard in `tests/conftest.py` and the `.claude` hook. It also fixes the recovery-bundle aborted-transaction bug that the PostgreSQL run exposed.
- Commit/PR/Opus-review rule and hook update: pushed to PR #33 (`chore/claude-code-guidance`, `c773286`).
- `0183` done: 21 test projects deleted. Project 1 is intact (167 issues, 12 sprints). `0153` cancelled.
- `0184` done: sprints `0119`, `0140`, `0168` closed. `0173`–`0175` cancelled as superseded. `0122`–`0128` and the `0140` issues returned to backlog.
- `0201`: fixtures received for relay67 (57 lines) and weather-app (49 lines). matterhub is pending (its session was offline).
- Follow-ups: `test_release_intake_sprint_assignment_and_board_filters` writes into the checkout's real `exports/`, so it should use a tmp dir. Add a unit test for `_alembic_revision` without `alembic_version`.

Next: write the `0204` ADR and get it Opus-reviewed. Then Phase C (`0185`, `0186`, `0176`) and Phase D in fresh sessions, one layer per PR.
