# Manual UAT Guide

Repeatable browser + MCP UAT for the MVP. Each step maps to a workflow in the Playwright catalog
(`tests/e2e/`, `ui-playwright` skill), so a human click-through and the automated run check the
same path. Record results in a copy of
[`../uat/TEMPLATE-local-uat.md`](../uat/TEMPLATE-local-uat.md) saved as
`documentation/uat/YYYY-MM-DD-<env>-uat.md`.

The steps are runtime-agnostic: they need a running app on a migrated PostgreSQL and its base URL.
Local Docker Compose commands are given below. For the k3s UAT cluster, use
[`k3s.md`](k3s.md) (issue 0020) to deploy, migrate, and get the URL, then start at
[Browser path](#browser-path).

## 1. Prerequisites (local Docker Compose)

Requires Docker with Compose v2; no host Python, virtualenv, PostgreSQL, or Alembic.

```bash
C="docker compose -f deployment/docker-compose.local.yml"
$C config -q
$C build
$C run --rm app alembic upgrade head          # explicit; app startup never migrates
$C run --rm app python -m pytest tests/
$C up -d
curl -fsS http://localhost:8000/health        # expect {"ok":true,"database":"ok"}
```

Base URL: `http://localhost:8000` (override the host port with `APP_HTTP_PORT`). If `/health`
does not report `"database":"ok"`, stop and record it as a runtime-gate blocker (issue 0008).

## 2. Data setup

Pick one per run and write it in the notes:

- **Manual entry** — follow the browser path below; the walkthrough creates its own data.
- **Demo project** — `$C run --rm app issue-tracker seed-demo` (optionally
  `--project-name "UAT Demo 2"`). Creates one project through the service layer and prints JSON:

  | ID | Kind | State after seeding |
  |---|---|---|
  | `0001` | issue "Demo blocker issue" (`DEMO-STATE`) | backlog; blocks `0002` |
  | `0002` | issue "Demo blocked issue" (`DEMO-STATE`) | in-progress; in sprint `0004` |
  | `0003` | issue "Demo closed issue" (`DEMO-UI`) | done; originating LLM `demo-seed`; issue-log entry |
  | `0004` | sprint "Demo UAT sprint" | active |
  | `0005` | issue "Demo backlog issue" | backlog (created after the sprint) |

  `0004`/`0005` show issues and sprints sharing one project-local `NNNN` sequence. Re-running with
  the same name prints `"created": false` and changes nothing. The command never deletes,
  truncates, or migrates, and the demo categories are ordinary project data.

## Browser path

For every page visited, also check styling: the page is visibly styled (not raw HTML), text fits
controls and tables, forms work with keyboard and mouse, the back link returns to the parent page,
and no secret values are shown. Check once at desktop width and once at phone width (~390px).

| # | Workflow (test) | Steps | Expected |
|---|---|---|---|
| 1 | W-SETUP (`test_00_setup.py::test_setup`) | Fresh DB: open `/` → redirected to `/setup`. Enter username `admin` and a local-only test password. Submit. Open `/setup` again. | Admin created, lands on the project list. `/setup` now redirects away. Password never shown. In devtools → Application → Cookies, the session cookie is `HttpOnly` and `SameSite=Lax` (and `Secure` when served over HTTPS). Do not copy the cookie value into notes. |
| 2 | W-AUTH (`test_auth_workflows.py::test_auth`) | Log out. Open `/` → redirected to `/login`. Submit a wrong password. Log in with the right one. | Inline "Invalid login" on the wrong password; correct password returns to the project list. |
| 3 | W-PROJECT (`test_project_workflows.py::test_project`) | Create project `Manual UAT Project` (repo URL optional). | Redirected to project detail; project listed on `/`. |
| 4 | W-CATEGORY (`test_project_workflows.py::test_category`) | On the project, add category key `UAT-1`, name `UAT state`, a one-line checklist. Open a different project. | Category listed and selectable in the issue form; not shown in the other project. |
| 5 | W-ISSUE-CREATE failure (`test_issue_workflows.py::test_create_issue`) | Submit issue `Missing AC UAT` with acceptance criteria empty, then with only spaces. | Browser blocks the empty field; whitespace-only submit shows inline "Acceptance criteria are required" on the project page. Issues table has no `Missing AC UAT` row. |
| 6 | W-ISSUE-CREATE success | Create `Prepare blocker` (category `UAT-1`, AC `- [ ] Blocker can be linked`) and `Complete blocked work` (AC `- [ ] Blocked issue can be closed`). | Each opens with a four-digit ID (`0001`, `0002` in a new project), status backlog, AC shown. |
| 7 | W-DEPENDENCY (`test_dependency`, `test_dependency_cycle_rejected`) | On `Complete blocked work`, add `Prepare blocker` as blocker. Then on `Prepare blocker`, add `Complete blocked work` as blocker. | Edge shown on both issues. Reverse edge shows "Dependency would create a cycle"; no new edge. |
| 8 | W-SPRINT (`test_sprint`) | On the project, create sprint `Local manual UAT sprint`. Add `Complete blocked work`. Close the sprint. | Sprint ID continues the issue sequence (e.g. `0003`). Issue listed on the sprint page; its issue status is `in-progress` (the sprint table's own column shows the membership state, `todo`). Sprint status becomes closed. |
| 9 | W-ISSUE-CLOSE (`test_close_issue`, `test_close_issue_blank_llm_rejected`, `test_closed_issue_metadata_and_reopen_blocked`) | On `Complete blocked work`, close with blank originating LLM. Then close with LLM `uat-llm` and note `Manual UAT close`. Then try to change status again. | Blank LLM → "Originating LLM is required to close an issue", still open. With LLM → `done`, LLM and note shown. Re-open/re-close → "Closed issue metadata is immutable"; metadata unchanged. |
| 10 | Issue log (no e2e test yet) | Return to the project page. With demo data, open `UAT Demo`. | "Issue log" section visible; empty state reads "No issue log entries yet."; demo project shows its entry. |

Automated equivalent of rows 1–9 (desktop + mobile, screenshot per step under `artifacts/e2e/`):

```bash
RUN_BROWSER_UAT=1 E2E_BASE_URL=http://localhost:8000 python -m pytest -q tests/e2e
```

Run it inside the app container (`$C run --rm -e RUN_BROWSER_UAT=1 -e E2E_BASE_URL=http://app:8000 app ...`)
or from any machine with Playwright Chromium. `W-SETUP` needs a database with no admin yet; on a
reused database it records that setup is already complete.

## MCP and import/export

MCP steps are in [`mcp.md`](mcp.md#uat-smoke). Import/export:

```bash
$C run --rm app issue-tracker export-json <project_id> exports/uat-project.json
$C run --rm app issue-tracker import-json exports/uat-project.json UAT-Restored          # must fail: mapping required
$C run --rm app issue-tracker import-json exports/uat-project.json UAT-Restored \
  --category-map DEMO-STATE=DEMO-STATE --category-map DEMO-UI=DEMO-UI
grep -ciE 'password|secret|session|database_url' exports/uat-project.json            # expect 0
```

`exports/` is gitignored; never commit an export.

## Local reset (local Docker Compose only)

> **Local development machine only.** This deletes the local Compose volume. It is not a
> deployment, UAT, or production procedure — never run it against a cluster, a shared database,
> or any `DATABASE_URL` you did not create on this machine. Cluster data changes go through
> [`k3s.md`](k3s.md) and [`backup-restore.md`](backup-restore.md).

```bash
docker compose -f deployment/docker-compose.local.yml down -v     # removes issue_tracker_pgdata
docker compose -f deployment/docker-compose.local.yml run --rm app alembic upgrade head
docker compose -f deployment/docker-compose.local.yml up -d
docker compose -f deployment/docker-compose.local.yml run --rm app issue-tracker seed-demo
```

Then start again at W-SETUP. Without a reset, `seed-demo --project-name "<new name>"` gives a fresh
demo project next to existing data; nothing is ever overwritten.

## Recording

Per step: Pass/Fail, evidence (screenshot path, command output line), blocker, and retry step.
Record any app bug as a new issue under `documentation/issues/` and link it in the notes'
Findings table; issue 0012 owns the release decision.
