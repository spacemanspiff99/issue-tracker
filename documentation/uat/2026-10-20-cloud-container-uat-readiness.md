# Local Manual UAT Notes — Cloud Container Readiness Run

Date: 2026-10-20
Tester: Claude Code (automated; no human click-through)
Commit SHA: `a98b164` (main) + this branch's changes (`seed-demo`, guides); app code under test unchanged from `a98b164`
Branch: `claude/0008-0011-uat-readiness`
Browser: Playwright Chromium (`/opt/pw-browsers/chromium`), desktop 1280×800 and mobile 390×844
Environment: ephemeral cloud container, Docker 29.9.1 daemon started in-session, Compose
`deployment/docker-compose.local.yml`, `postgres:16-alpine`, fresh volume (`down -v` first)

Covers issues [0008](../issues/0008-local-runtime-gate.md), [0009](../issues/0009-manual-web-uat-script.md),
[0010](../issues/0010-demo-data-and-reset-safe-uat.md), [0011](../issues/0011-mcp-local-uat-smoke.md).
Release decision stays with [0012](../issues/0012-uat-findings-and-release-decision.md).

## Environment deviations (read first)

- The container's network policy denies `deb.debian.org` (proxy 403), so the Dockerfile's
  `playwright install --with-deps chromium` layer cannot run here. The image was built from the
  same context with that one line removed (scratch copy, not committed) via
  `docker build --network host -f <scratch>/Dockerfile.nodeps -t deployment-app .`, on a
  local-only `python:3.12-slim` tag that adds the session proxy CA. `docker compose ... build` as written was not proven here; CI's `e2e` job proved it on a
  clean runner ([run](https://github.com/spacemanspiff99/issue-tracker/actions/runs/39466799278/job/118780179039)).
- Because of that, the e2e suite ran from the host Chromium against the compose app on
  `localhost:8000`, not inside the app container.

## Runtime Gate

| Check | Command or step | Pass/Fail | Evidence | Blocker or notes |
|---|---|---|---|---|
| Compose config | `docker compose -f deployment/docker-compose.local.yml config -q` | Pass | exit 0 | |
| Build | `docker compose -f deployment/docker-compose.local.yml build` | Pass (CI) / blocked here | CI `e2e` `up -d --build` on `c10970f`: [run](https://github.com/spacemanspiff99/issue-tracker/actions/runs/39466799278/job/118780179039). Here: `failed to resolve ... python:3.12-slim: 429` then apt `403 Forbidden` for `deb.debian.org` | Environment network policy; app layers (pip install `-e .[dev]`) built fine. |
| Migration | `... run --rm app alembic upgrade head` (fresh volume) | Pass | `0001_initial → 0002 → 0003 → 0004_reconcile_schema_drift` | |
| Lint | `... run --rm app python -m ruff check .` | Fail (tooling) | `.ruff_cache` not writable by `appuser` | [0027](../issues/0027-ruff-in-app-container-cache-permission.md); `--no-cache`: `All checks passed!` |
| Tests | `... run --rm app python -m pytest tests/` | Pass | `22 passed, 22 skipped` (skips = e2e without `RUN_BROWSER_UAT`) | |
| Stack | `... up -d` | Pass | `app running`, `postgres running` | |
| Health | `curl -fsS http://localhost:8000/health` | Pass | `{"ok":true,"database":"ok"}` | |

## Web UAT (Playwright catalog — automated stand-in for the click-through)

`RUN_BROWSER_UAT=1 PLAYWRIGHT_CHROMIUM_EXECUTABLE=/opt/pw-browsers/chromium python -m pytest -q tests/e2e`
→ **22 passed in 38s** on `a98b164`; 70 screenshots (35 desktop, 35 mobile) in `artifacts/e2e/`
(local, gitignored; CI uploads the same folder). Before 0019 merged, the same run on `680169a` was
16 passed + 6 strict xfails (all `BUG_0019`).

| Step | Expected result | Pass/Fail | Evidence | Blocker or notes |
|---|---|---|---|---|
| First-run setup (W-SETUP) | Admin created; `/setup` then redirects | Pass | `test_setup` | Volume already set up by an earlier run on this volume; redirect branch observed |
| Login/logout (W-AUTH) | Bad password → "Invalid login"; login works | Pass | `test_auth` | |
| Project creation (W-PROJECT) | Project appears and opens | Pass | `test_project` | |
| Category creation (W-CATEGORY) | Project-scoped and selectable | Pass | `test_category` | |
| Missing AC validation | Inline error; no row | Pass | `test_create_issue` steps 02–03; screenshot `03-blank-ac-server-error-desktop.png` reviewed | |
| Issue creation | Four-digit IDs | Pass | `test_create_issue` step 04 | |
| Dependency creation | Edge both sides; reverse edge rejected | Pass | `test_dependency`, `test_dependency_cycle_rejected` | |
| Sprint creation / assignment / close | Shared sequence; issue added; closed | Pass | `test_sprint`; screenshot `03-issue-added-to-sprint-mobile.png` reviewed | |
| Issue close | Blank LLM rejected; metadata shown; re-close rejected | Pass | `test_close_issue`, `test_close_issue_blank_llm_rejected`, `test_closed_issue_metadata_and_reopen_blocked` | |
| Issue log view | Section visible | Pass | Every project-page screenshot shows "Issue log" + empty state | No dedicated e2e test |
| Styling sanity | Styled, usable desktop + mobile | Pass (automated review) | Reviewed project page (desktop) and sprint page (mobile) screenshots | Human pass still owed |
| Human click-through | Guide followed by a person | Not run | — | Owner, per `documentation/guides/manual-uat.md` |

## Demo Data UAT

| Check | Command or step | Pass/Fail | Evidence | Blocker or notes |
|---|---|---|---|---|
| Seed | `... run --rm app issue-tracker seed-demo` | Pass | `{"created": true, "issues": {"0001": ..., "0002": ..., "0003": ..., "0005": ...}, "sprint": "0004", ...}` | Shared sequence visible (sprint 0004 between issues) |
| Re-run is a no-op | same command again | Pass | `{"created": false, "project": "UAT Demo", "project_id": 21}` | |
| Unit tests | `pytest tests/integration/test_demo_data.py` | Pass | 4 passed (deterministic IDs, no-op rerun, other projects untouched, secret-free export) | |

## MCP UAT

| Check | Command or step | Pass/Fail | Evidence | Blocker or notes |
|---|---|---|---|---|
| MCP smoke | `python -m issue_tracker.mcp.server --smoke` | Pass | `{"ok": true, "tools": [11 names]}`; equals `mcp.md` list (`diff` empty) | Static list only |
| Compact output | `python -m pytest tests/integration/test_mcp_tools.py` | Pass | `3 passed` | |
| Live tool calls (service layer, demo project 21) | scratch script calling `mcp/tools.py` | Pass | search default 449 B, `limit=2` 240 B, `limit=500` echoes effective limit 50 (service clamps to 1–50 in `IssueService.search`; only 26 issues existed, so the row cap was not exercised live, and no test asserts it yet — added to [0026](../issues/0026-mcp-project-list-unbounded.md)); `issue.get` compact 115 B / full 265 B; mutations 77–177 B; no `acceptance_criteria` outside `include_full` | `project.list` 1,508 B, unbounded → [0026](../issues/0026-mcp-project-list-unbounded.md) |
| Stdio server | initialize + `tools/list` + `tools/call` over stdio | **Fail** | stdout 0 lines; stderr `mcp package is required to run the stdio server` (mcp 2.x installed) | [0025](../issues/0025-mcp-2x-breaks-stdio-server.md). With `mcp<2` in a throwaway container: 3 JSON-RPC lines on stdout, logs on stderr only |

## Import Export UAT

| Check | Command or step | Pass/Fail | Evidence | Blocker or notes |
|---|---|---|---|---|
| Export JSON | `issue-tracker export-json 21 exports/uat-demo.json` | Pass | file written; `git check-ignore` → `.gitignore:34:exports/` | |
| Import without mapping | `issue-tracker import-json exports/uat-demo.json UAT-Restored` | Pass (rejected) | `Import with source categories requires explicit category mapping`, exit 1 | |
| Import with mapping | `... --category-map DEMO-STATE=DEMO-STATE --category-map DEMO-UI=DEMO-UI` | Pass | printed new project id `22` | |
| Secret safety | `grep -ciE 'password\|secret\|session\|database_url' exports/uat-demo.json` | Pass | `0` | |

## Findings

| Finding | Severity | Follow-up issue | Owner action | Status |
|---|---|---|---|---|
| MCP stdio server cannot start with mcp 2.x (`mcp>=1.2` unpinned) | High (agent-facing half of MVP unusable on fresh build) | [0025](../issues/0025-mcp-2x-breaks-stdio-server.md) | Approve the pin/port | Open |
| `project.list` has no `limit` | Low | [0026](../issues/0026-mcp-project-list-unbounded.md) | — | Open |
| In-container `ruff check` fails on cache dir permissions | Low (tooling) | [0027](../issues/0027-ruff-in-app-container-cache-permission.md) | — | Open |

## Decision

Local manual UAT **not ready** as of `a98b164` — BLOCKED: MCP stdio server — fails to start on a
fresh build ([0025](../issues/0025-mcp-2x-breaks-stdio-server.md)) — fix 0025, then re-run the
stdio script. Also owed before "ready": a
human click-through of `documentation/guides/manual-uat.md`. Web runtime, migrations, unit/integration
tests, `/health`, and the full Playwright catalog passed on this SHA.
