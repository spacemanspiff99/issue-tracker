# Issue 0009: Manual Web UAT Script

Status: in-progress — dev-path (Compose) AC pass at `cac4a09`; k3s UAT AC marked OWNER are open.
Recommended model: GPT-5.5 medium
Category gates: `IT-1`, `IT-2`, `IT-5`, `IT-6`
Sprint: Sprint 0007

## Problem

The project needs a repeatable local manual UAT script that a human can run in the browser without guessing the intended MVP path.

## Scope

- Create or update a manual UAT guide under `documentation/guides/`.
- Cover first-run setup, login, project creation, category creation, issue creation validation, dependency creation, sprint creation, sprint issue assignment, issue close with originating LLM, and issue-log viewing.
- Include expected results, notes fields, and pass/fail recording guidance.
- Include browser styling sanity checks so raw HTML or broken CSS is caught.

## Acceptance Criteria

Guide: [`../guides/manual-uat.md`](../guides/manual-uat.md) (`cac4a09` + docs commits on this PR).

- [x] Manual UAT guide names the exact URL and startup prerequisites → target table: UAT `http://issue-tracker-uat.home.arpa` (k3s `issue-tracker-uat`), dev `http://localhost:8000` (Compose, rehearsal only), production never; §1 lists the pipeline run, digest check, namespace check and `/health`.
- [x] Guide targets the k3s UAT, with Compose/local only as the dev path → §1–2, browser path, UAT reset are k3s; Compose is boxed under "Dev rehearsal (local Docker Compose only)".
- [x] Guide includes setup/login path and expected session-cookie behavior at a high level without exposing secrets → row W-SETUP/W-AUTH; cookie `HttpOnly` + `SameSite=Lax`, no `Secure` on the plain-HTTP UAT ingress (`SESSION_COOKIE_SECURE="false"`); admin password read from the UAT Secret, never written into notes.
- [x] Guide proves creating an issue without acceptance criteria shows validation and does not create a row → row 5 (whitespace-only AC → "Acceptance criteria are required", no row); covered by `test_issue_workflows.py::test_create_issue`.
- [x] Guide covers project, category, issue, dependency, sprint, sprint assignment, close metadata, and issue-log viewing → rows 3–10.
- [x] Guide includes a page styling sanity check for each main page → "For every page visited…" at desktop and ~390px.
- [x] Guide includes a UAT notes template with pass/fail, blocker, evidence, and retry fields → [`../uat/TEMPLATE-local-uat.md`](../uat/TEMPLATE-local-uat.md) + "Recording".
- [x] The guide's browser path is driven end to end by Playwright on the dev path → `RUN_BROWSER_UAT=1 E2E_BASE_URL=http://localhost:8000 python -m pytest -q tests/e2e` against the fresh compose stack: `22 passed in 40.11s`, 72 screenshots under `artifacts/e2e/` (`cac4a09`).
- [ ] **OWNER** — On UAT: `deployment/k8s/e2e.sh issue-tracker-uat` → `22 passed`, screenshots in `artifacts/e2e-k8s/` (the pipeline run in 0008 also covers this). Then a human click-through of the guide at `http://issue-tracker-uat.home.arpa`, notes saved as `documentation/uat/YYYY-MM-DD-k3s-uat-uat.md` and linked from 0012.

Originating model: claude-opus-5-5 (effort: medium).

## Category Checklists

`IT-1` Tracker State Integrity: Verify project-local sequence allocation, status transitions, dependency cycle rejection, and immutable close metadata.

`IT-2` Category And AC Binding: Verify acceptance criteria are required, category checklists are inlined when applicable, and project taxonomies remain project-scoped data.

`IT-5` Auth And Secret Safety: Verify password hashing, session flags, setup flow, secret handling, and no credential logging.

`IT-6` Deployment And Configuration Drift: Verify compose files, env vars, health checks, explicit migrations, and workflow behavior stay aligned.

## Verification Commands

```bash
deployment/k8s/e2e.sh issue-tracker-uat                    # owner; refuses issue-tracker
RUN_BROWSER_UAT=1 E2E_BASE_URL=http://localhost:8000 python -m pytest -q tests/e2e   # dev path
```

Manual browser verification follows the guide.

## STOP

Stop when the guide can be followed from a fresh local stack, or record the first failing step and the evidence needed to debug it.
