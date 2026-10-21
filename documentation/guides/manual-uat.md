# Manual UAT Guide

Repeatable browser + MCP UAT for the MVP. Each step maps to a workflow in the Playwright catalog
(`tests/e2e/`, `ui-playwright` skill), so a human click-through and the automated run check the
same path. Record results in a copy of
[`../uat/TEMPLATE-local-uat.md`](../uat/TEMPLATE-local-uat.md) saved as
`documentation/uat/YYYY-MM-DD-<env>-uat.md`.

| Target | Where | Base URL | Use |
|---|---|---|---|
| **UAT** | k3s namespace `issue-tracker-uat` ([`k3s.md`](k3s.md), issue 0020) | `http://issue-tracker-uat.home.arpa` | The UAT. Owner sign-off and the 0012 release decision use this. |
| Dev | Local Docker Compose ([`local-development.md`](local-development.md)) | `http://localhost:8000` | Developer rehearsal only; never a UAT result. |
| Production | k3s namespace `issue-tracker` | — | **Never** a UAT target. Demo data and resets refuse it. |

## 1. UAT prerequisites (k3s `issue-tracker-uat`)

Run from the owner machine with cluster access (never from a cloud session). Every command names
the UAT namespace explicitly:

```bash
K="kubectl -n issue-tracker-uat"
```

1. Deploy the commit under test: Actions → **k3s UAT Production Pipeline** → Run workflow on
   `main` with `promote_prod: false` ([`k3s.md`](k3s.md) step 9/10). The run must show the backup
   dump, `alembic upgrade head`, rollout complete, `health: {"ok": true, "database": "ok"}` (pod and
   ingress), and the browser suite passing with screenshots in `uat-e2e-screenshots-<sha>`.
2. Confirm what UAT runs and that it is healthy:

```bash
$K get deploy issue-tracker -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
#   ghcr.io/spacemanspiff99/issue-tracker@sha256:...   (same digest as the pipeline run)
$K exec deploy/issue-tracker -- cat /var/run/secrets/kubernetes.io/serviceaccount/namespace; echo
#   issue-tracker-uat
curl -fsS http://issue-tracker-uat.home.arpa/health
#   {"ok":true,"database":"ok"}
```

If `/health` does not report `"database":"ok"`, stop and record a runtime-gate blocker (issue
0008). The UAT admin password is the `issue-tracker-app` Secret's `E2E_ADMIN_PASSWORD` (or
`ADMIN_INITIAL_PASSWORD`) in `issue-tracker-uat`; never write it into notes.

## 2. Data setup

Pick one per run and write it in the notes:

- **Manual entry** — follow the browser path below; the walkthrough creates its own data.
- **Demo project** — run `seed-demo` inside the UAT app pod (optionally
  `--project-name "UAT Demo 2026-10-21"`):

```bash
$K exec deploy/issue-tracker -- issue-tracker seed-demo
#   {"categories": ["DEMO-STATE", "DEMO-UI"], "created": true, "issues": {"0001": ..., "0005": ...},
#    "project": "UAT Demo", "project_id": <id>, "sprint": "0004"}
```

  It creates one project through the service layer:

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

  **Target guard.** `seed-demo` refuses (exit 1, before opening a database session) unless the
  target is UAT or local: in a pod it reads the namespace from the service-account file (or
  `POD_NAMESPACE`) and accepts only `issue-tracker-uat` with the in-namespace Postgres; outside a
  cluster it accepts only SQLite or a `localhost`/`127.0.0.1`/`::1`/`postgres` (Compose) host.

  | Target | Output |
  |---|---|
  | pod in `issue-tracker` (production) | `refusing seed-demo: namespace 'issue-tracker' is production` |
  | pod in any other namespace | `refusing seed-demo: namespace '<ns>' is not 'issue-tracker-uat'` |
  | pod with no readable namespace | `refusing seed-demo: running in a cluster but the namespace is unknown` |
  | any non-local host (e.g. a LAN IP) | `refusing seed-demo: database host '<host>' is not local or issue-tracker-uat` |

  A `kubectl port-forward` makes any database look like `localhost`, so never run `seed-demo`
  through a port-forward; on UAT always use the `kubectl exec` form above.

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

Automated equivalent of rows 1–9 (desktop + mobile, screenshot per step): the pipeline's UAT job
runs it on every deploy. To re-run it against UAT without redeploying:

```bash
deployment/k8s/e2e.sh issue-tracker-uat     # refuses issue-tracker; screenshots in artifacts/e2e-k8s/
#   ... 22 passed
```

On UAT the pipeline's browser suite has already done first-run setup, so W-SETUP records "setup
already complete": log in with the UAT admin password instead. The ingress is plain HTTP, so the
session cookie is `HttpOnly` + `SameSite=Lax` without `Secure` (`SESSION_COOKIE_SECURE="false"`,
[`k3s.md`](k3s.md)).

## MCP and import/export

MCP steps are in [`mcp.md`](mcp.md#uat-smoke). Import/export on UAT (the file stays in the pod's
`/tmp` and never leaves it except through the grep count):

```bash
$K exec deploy/issue-tracker -- issue-tracker export-json <project_id> /tmp/uat-project.json
$K exec deploy/issue-tracker -- issue-tracker import-json /tmp/uat-project.json UAT-Restored
#   Import with source categories requires explicit category mapping   (exit 1, no project)
$K exec deploy/issue-tracker -- issue-tracker import-json /tmp/uat-project.json UAT-Restored \
  --category-map DEMO-STATE=DEMO-STATE --category-map DEMO-UI=DEMO-UI
#   <new project id>
$K exec deploy/issue-tracker -- sh -c "grep -ciE 'password|secret|session|database_url' /tmp/uat-project.json; rm -f /tmp/uat-project.json"
#   0
```

Never copy an export into the repository.

## UAT reset (k3s `issue-tracker-uat` only)

Never delete a PVC or namespace to reset ([`k3s.md`](k3s.md#rollback)).

- **Soft reset (default).** Seed a new, dated demo project next to the old data; nothing is
  overwritten: `$K exec deploy/issue-tracker -- issue-tracker seed-demo --project-name "UAT Demo $(date +%F)"`.
- **Hard reset** (only when UAT must be empty again). Restore a baseline dump with the UAT kubeconfig
  (context `issue-tracker-uat`, [`k3s.md`](k3s.md) step 3), then redeploy UAT so it migrates to
  head. The `uat` argument maps to `issue-tracker-uat` only; there is no reset path for production.

```bash
export KUBECONFIG=./kubeconfig-uat.yaml        # can act only in issue-tracker-uat
# Once, right after the first UAT deploy: keep its pre-migration dump (empty DB) as the baseline,
# because pre-migration/ keeps only the newest 5.
deployment/k8s/backup-files.sh uat list
deployment/k8s/backup-files.sh uat get /backups/pre-migration/<first-sha>-<ts>.dump ./uat-baseline
deployment/k8s/backup-files.sh uat put ./uat-baseline/<first-sha>-<ts>.dump uat-baseline.dump
# Each hard reset:
CONFIRM=issue-tracker-uat deployment/k8s/restore.sh uat /backups/imports/uat-baseline.dump
# then run the pipeline with promote_prod: false, and seed-demo again
```

  `restore.sh` refuses: without `CONFIRM=issue-tracker-uat` (exit 2, `refusing: set
  CONFIRM=issue-tracker-uat ...`); with `CONFIRM=issue-tracker`; under any context other than
  `issue-tracker-uat` (`refusing: context '<ctx>', expected 'issue-tracker-uat'`); and with an
  unknown environment name such as `issue-tracker` (`unknown environment`).

## Dev rehearsal (local Docker Compose only)

> **Local development machine only.** Not a UAT result, not a deployment procedure. The reset
> below deletes the local Compose volume; never run it against a cluster, a shared database, or
> any `DATABASE_URL` you did not create on this machine.

```bash
C="docker compose -f deployment/docker-compose.local.yml"
$C config -q && $C build
$C run --rm app alembic upgrade head          # explicit; app startup never migrates
$C run --rm app python -m pytest tests/
$C up -d && curl -fsS http://localhost:8000/health          # {"ok":true,"database":"ok"}
$C run --rm app issue-tracker seed-demo
RUN_BROWSER_UAT=1 E2E_BASE_URL=http://localhost:8000 python -m pytest -q tests/e2e   # or in the app container with E2E_BASE_URL=http://app:8000
```

Local reset:

```bash
docker compose -f deployment/docker-compose.local.yml down -v     # removes issue_tracker_pgdata
docker compose -f deployment/docker-compose.local.yml run --rm app alembic upgrade head
docker compose -f deployment/docker-compose.local.yml up -d
docker compose -f deployment/docker-compose.local.yml run --rm app issue-tracker seed-demo
```

The browser path above works unchanged at `http://localhost:8000`; locally `W-SETUP` runs on the
fresh volume. Local import/export uses `$C run --rm app issue-tracker export-json ... exports/...`
(`exports/` is gitignored).

## Recording

Per step: Pass/Fail, evidence (screenshot path, command output line), blocker, and retry step.
Record any app bug as a new issue under `documentation/issues/` and link it in the notes'
Findings table; issue 0012 owns the release decision.
