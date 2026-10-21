# Issue 0010: Demo Data And Reset-Safe UAT Commands

Status: in-progress — dev-path (Compose) AC pass at `cac4a09`; k3s UAT AC marked OWNER are open.
Recommended model: GPT-5.5 high
Category gates: `IT-1`, `IT-2`, `IT-6`
Sprint: Sprint 0007

## Problem

Manual UAT needs deterministic data setup and reset instructions that do not rely on hidden database mutation or unsafe production-like commands.

## Scope

- Decide whether UAT uses manual data entry only, a seed command, or an import JSON fixture.
- If a fixture is used, keep it secret-free and small.
- Document reset steps using Docker Compose volumes only for local development.
- Make clear that app startup does not auto-drop, truncate, recreate, or silently migrate databases.

## Acceptance Criteria

Decision: seed command, no committed fixture. `issue-tracker seed-demo [--project-name NAME]`
(`src/issue_tracker/demo_data.py`; target guard `seed_demo_refusal` in `src/issue_tracker/cli.py`)
creates one project through the service layer; re-running with an existing name is a no-op; it
never deletes, truncates, or migrates.

- [x] UAT data setup path is documented and repeatable → [`manual-uat.md` §2](../guides/manual-uat.md#2-data-setup): `kubectl -n issue-tracker-uat exec deploy/issue-tracker -- issue-tracker seed-demo`. Dev path at `cac4a09`: first run → `"created": true`, issues `0001`–`0003`, sprint `0004`, issue `0005`; rerun → `{"created": false, "project": "UAT Demo", "project_id": 21}`.
- [x] Any fixture contains no secrets, password hashes, sessions, environment values, logs, dumps, or backups → no fixture committed; `test_seed_demo_export_is_secret_free` passes; export of the demo greps `0` for `password|secret|session|database_url`.
- [x] Demo data refuses the production namespace and any DB that isn't UAT/local → `tests/integration/test_demo_data.py`: `13 passed` (`cac4a09`), incl. 7 refusal cases and a test that `main()` exits before opening a session. In the compose app container (`cac4a09`), each exit 1 with no DB connection: `POD_NAMESPACE=issue-tracker` → `refusing seed-demo: namespace 'issue-tracker' is production`; `POD_NAMESPACE=default` → `… is not 'issue-tracker-uat'`; `KUBERNETES_SERVICE_HOST` set, no namespace → `… namespace is unknown`; `DATABASE_URL=…@192.168.10.8…` → `… database host '192.168.10.8' is not local or issue-tracker-uat` (refused before any connection; the host was never contacted).
- [x] Reset instructions refuse production and cannot be mistaken for deployment guidance → [`manual-uat.md` "UAT reset"](../guides/manual-uat.md#uat-reset-k3s-issue-tracker-uat-only): soft reset = new dated demo project; hard reset = `CONFIRM=issue-tracker-uat restore.sh uat …` with the UAT kubeconfig (RBAC: no rights in `issue-tracker`). Offline check with a stub `kubectl` (no cluster): no `CONFIRM` → `refusing: set CONFIRM=issue-tracker-uat …` exit 2; `CONFIRM=issue-tracker` → same, exit 2; context `issue-tracker-prod` → `refusing: context 'issue-tracker-prod', expected 'issue-tracker-uat'` exit 2; env name `issue-tracker` → `unknown environment` exit 2. Compose `down -v` reset is boxed as local-machine-only.
- [x] Import path requires explicit project and category mapping when source categories are present → `import-json` without `--category-map` → `Import with source categories requires explicit category mapping`, exit 1 (`test_cli_import_export.py`, passing at `cac4a09`).
- [x] Shared `NNNN` issue/sprint sequence behavior is visible in the UAT data → sprint `0004` between issues `0003` and `0005` (`test_seed_demo_is_deterministic_and_shows_shared_sequence`).
- [ ] **OWNER** — On UAT: `kubectl -n issue-tracker-uat exec deploy/issue-tracker -- cat /var/run/secrets/kubernetes.io/serviceaccount/namespace` → `issue-tracker-uat`; `kubectl -n issue-tracker-uat exec deploy/issue-tracker -- issue-tracker seed-demo` → JSON with `"created": true`, `"sprint": "0004"`; same command again → `"created": false`.
- [ ] **OWNER** — After the first production deploy (read-only check; the guard exits before any DB session): `kubectl -n issue-tracker exec deploy/issue-tracker -- issue-tracker seed-demo; echo "exit=$?"` → `refusing seed-demo: namespace 'issue-tracker' is production` and `exit=1`.

Originating model: claude-opus-5-5 (effort: medium).

## Category Checklists

`IT-1` Tracker State Integrity: Verify project-local sequence allocation, status transitions, dependency cycle rejection, and immutable close metadata.

`IT-2` Category And AC Binding: Verify acceptance criteria are required, category checklists are inlined when applicable, and project taxonomies remain project-scoped data.

`IT-6` Deployment And Configuration Drift: Verify compose files, env vars, health checks, explicit migrations, and workflow behavior stay aligned.

## Verification Commands

```bash
python -m pytest -q tests/integration/test_demo_data.py tests/integration/test_cli_import_export.py
docker compose -f deployment/docker-compose.local.yml run --rm app issue-tracker seed-demo        # dev path
docker compose -f deployment/docker-compose.local.yml run --rm -T -e POD_NAMESPACE=issue-tracker app issue-tracker seed-demo   # must refuse
kubectl -n issue-tracker-uat exec deploy/issue-tracker -- issue-tracker seed-demo                 # owner, UAT
```

## STOP

Stop when a reviewer can reset and recreate the UAT data without touching production or committing generated artifacts.
