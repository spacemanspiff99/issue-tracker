# Prompt: Fix Deployment Source-Of-Truth Rules And Prepare UAT For Comprehensive Testing

Use this prompt in a fresh Codex session. Do not continue in the same session that created this prompt.

## Context

Repository: `/home/akun/issue-tracker`

Recent incident:

- The user said "deploy to UAT" expecting UAT to match the current dev application state.
- The GitHub Actions pipeline deployed a pushed PR branch, but the dev checkout had many uncommitted product/UI changes that GitHub Actions could not see.
- UAT therefore did not look like dev.
- Local Docker preflight from a temporary worktree reused the default Compose project/container names on the dev host and disrupted the live dev app at `192.168.10.20:8000`.
- Dev was restored by restarting the app container against the existing local Postgres volume.

Required operational contract:

- Dev URL: `http://192.168.10.20:8000`
- UAT host: `app-uat`, `192.168.10.26`, SSH user `akun`
- Prod host: `app-prod`, `192.168.10.27`, SSH user `akun`
- Normal UAT and prod deploys move committed code only.
- UAT deploys must preserve the existing UAT database.
- Prod deploys must preserve the existing prod database.
- Production data is the durable source of truth.
- Copying prod data down to UAT or dev for realistic testing must be a separate explicit data refresh workflow, never part of normal deploy.
- Never copy dev or UAT data upward into production.

There is already a PR for app host deployment target updates:

- PR: `https://github.com/spacemanspiff99/issue-tracker/pull/4`
- Branch: `deploy/app-host-targets`
- Latest known successful UAT workflow run: `26202657276`
- Latest deployed UAT commit in that run: `6f0997054764aac938fe39965686e286208590fc`

Important: the local checkout may contain substantial uncommitted application work. Preserve user work. Do not revert unrelated changes.

## Required Model And Reasoning

Use GPT-5.5 high for this prompt. This is deployment-, data-, and release-safety work.

If GPT-5.5 is unavailable, use the strongest available model and explicitly record the mismatch in the final handoff.

## Rules To Load

Read these first:

- `AGENTS.md`
- `.cursor/rules/core.mdc`
- `.cursor/rules/agents.mdc`
- `.cursor/rules/ac.mdc`
- `.cursor/rules/devops.mdc`
- `documentation/guides/deployment.md`
- `documentation/guides/comprehensive-test-plan.md`
- `documentation/guides/manual-uat.md`
- `documentation/guides/backup-restore.md`

## Start Procedure

1. Inspect the repo state:

```bash
git status --short --branch
git branch --show-current
git rev-parse HEAD
git rev-parse --abbrev-ref --symbolic-full-name @{u}
git rev-parse @{u}
```

2. Identify which local changes are deployment/rules/docs changes versus unrelated app/product work.
3. Do not deploy anything until the intended code state is committed and pushed, or the user explicitly approves deploying a named older SHA.
4. Do not use a temporary worktree with the default Docker Compose project name on the dev host. If local Docker preflight is needed from a temp worktree, set a unique project name, for example:

```bash
COMPOSE_PROJECT_NAME=issue_tracker_preflight docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/
```

5. Confirm dev remains reachable before and after any local Docker preflight:

```bash
curl -fsS http://192.168.10.20:8000/health
```

## Files In Scope

Deployment and workflow hardening:

- `.github/workflows/local-pipeline.yml`
- `deployment/scripts/remote-compose-deploy.sh`
- `deployment/docker-compose.local.yml`
- `deployment/docker-compose.app.yml`
- `.env.example` if placeholders need clarification only

Rules and docs:

- `AGENTS.md`
- `.cursor/rules/devops.mdc`
- `.cursor/rules/core.mdc` only if rule indexing changes
- `documentation/guides/deployment.md`
- `documentation/guides/comprehensive-test-plan.md`
- `documentation/guides/backup-restore.md`
- `documentation/guides/manual-uat.md`
- `README.md` if deployment docs are linked there
- `documentation/uat/` for test evidence

Tests:

- Existing unit/integration/e2e tests
- Add script tests only if the repo has an established pattern or if shell behavior is complex enough to warrant a small test helper.

Avoid unrelated product/UI implementation unless required to get UAT to the committed dev state selected by the user.

## Implementation Requirements

### 1. Source-Of-Truth Deploy Gate

Make the UAT/prod deployment process visibly enforce or document:

- The exact Git branch/ref and SHA being deployed.
- Local uncommitted product/UI/schema/deployment/docs changes block "deploy current dev to UAT" unless the user explicitly chooses an older SHA.
- The workflow must not imply it can deploy uncommitted files.
- The final deployment report must state the deployed SHA and target environment.

Implement the strongest practical guard available in repo scripts/workflows. If a guard cannot be enforced inside GitHub Actions because Actions only sees the pushed ref, document the required operator-side preflight in the workflow docs and project rules.

### 2. Preserve Target Databases During Deploy

Verify and, if needed, improve deploy scripts so normal deploys:

- Take a pre-migration backup for UAT and prod before Alembic.
- Run only `alembic upgrade head`.
- Do not drop, recreate, truncate, reset, or overwrite target databases.
- Do not reset Docker volumes.
- Fail before migration if backup creation or backup copy fails.
- Preserve rollback/restore notes in logs/docs.
- For prod, refuse `SKIP_DB_BACKUP=1`.

### 3. Production Data Safety

Add or tighten docs/rules so production deploys are unambiguous:

- Prod data persists across deploys.
- Prod deploys are code/migration operations only.
- Prod deploys never copy data from UAT/dev into prod.
- Production restores require explicit user request naming the backup.
- Production `.env` and secrets are never copied to lower environments.

### 4. Prod-To-UAT/Dev Data Refresh Plan

Create a documented workflow for copying production data down to UAT or dev for testing. This is a plan and/or script design unless the user explicitly asks to execute it.

The workflow must require:

- Source must be `prod`.
- Target must be `uat` or `dev`.
- Explicit confirmation that target data will be overwritten.
- Production remains read-only except for dump/backup.
- Target backup is taken before overwrite.
- Source dump identity and target backup path are recorded.
- Secrets, `.env`, tokens, and runtime config are not copied.
- Session/token/password-hash handling is documented. If the app cannot sanitize these yet, document the limitation and require target-only admin setup/reset steps.
- Post-restore verification runs Alembic, `/health`, MCP smoke, and route/browser checks on the target.

Do not implement an unsafe one-command destructive refresh unless it has strong confirmations and dry-run behavior.

### 5. Local Docker Preflight Isolation

Fix the rules/docs and, where practical, commands so local preflight from temp worktrees does not disrupt the live dev app:

- Use unique `COMPOSE_PROJECT_NAME` for temp-worktree Docker checks.
- Avoid fixed `container_name` collisions for preflight when possible, or document that fixed container names make isolated preflight impossible until compose is changed.
- If changing Compose, preserve current dev and deploy behavior and test `docker compose config`.
- Do not stop or recreate the live dev app unless the user explicitly asks.

### 6. UAT Comprehensive Testing Readiness

Prepare UAT for comprehensive testing using committed code only:

- Confirm UAT deploy target is `app-uat` / `192.168.10.26`.
- Confirm the exact branch/SHA intended for UAT.
- Run local preflight without disrupting dev.
- Push the intended branch/ref.
- Dispatch the GitHub Actions UAT workflow with `deploy_prod=false`.
- Verify:
  - host/IP/hostname safety checks
  - image build
  - pre-migration backup
  - Alembic migration
  - tests
  - ruff
  - `/health`
  - MCP smoke
  - browser or route-level UAT
- Record pass/fail evidence under `documentation/uat/`.

If browser-level tests do not exist, do not fake them. Either:

- add a small meaningful e2e/browser smoke suite, or
- record that browser UAT remains manual and list the exact manual checks to perform.

## Acceptance Criteria

- `AGENTS.md`, `.cursor/rules/devops.mdc`, and deployment docs clearly state that UAT/prod deploys preserve target data and deploy committed code only.
- Deployment docs clearly distinguish normal deploy from prod-to-UAT/dev data refresh.
- A prod-to-UAT/dev refresh plan exists with backup-first, target-overwrite confirmation, and post-restore verification requirements.
- Local Docker preflight guidance prevents temp-worktree checks from recreating the live dev app containers.
- Workflow/script changes, if any, keep UAT host checks at `192.168.10.26` and prod host checks at `192.168.10.27`.
- Prod deploy rules do not reuse UAT DB/env/config and require prod-specific env values.
- UAT is deployed from a named pushed branch/SHA or the prompt stops with a clear reason.
- UAT data is preserved during deployment.
- UAT readiness evidence is recorded in `documentation/uat/`.
- No secrets, `.env` files, database dumps, generated backups, or large local artifacts are committed.

## Verification Commands

Run the relevant subset and report exact results:

```bash
git status --short --branch
bash -n deployment/scripts/remote-compose-deploy.sh
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/local-pipeline.yml')); print('workflow yaml ok')"
docker compose -f deployment/docker-compose.local.yml config
COMPOSE_PROJECT_NAME=issue_tracker_preflight docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/
COMPOSE_PROJECT_NAME=issue_tracker_preflight docker compose -f deployment/docker-compose.local.yml run --rm app python -m ruff check --no-cache .
curl -fsS http://192.168.10.20:8000/health
curl -fsS http://192.168.10.26:8000/health
```

For the actual UAT deploy, use GitHub Actions, not a manual SSH deploy, unless the user explicitly asks otherwise:

```bash
gh workflow run local-pipeline.yml --ref <branch-or-sha> \
  -f uat_host=192.168.10.26 \
  -f prod_host=192.168.10.27 \
  -f deploy_user=akun \
  -f deploy_path=/home/akun/issue-tracker \
  -f prod_env_file=/home/akun/issue-tracker/prod.env \
  -f deploy_prod=false
```

Watch the run and capture the run ID:

```bash
gh run list --workflow local-pipeline.yml --limit 5
gh run watch <run-id> --exit-status
```

## STOP

Stop only when one of these is true:

- UAT is ready for comprehensive testing and the final report names the deployed SHA, workflow run ID, target URL, preserved data behavior, and evidence file.
- A source-of-truth mismatch remains, such as uncommitted dev changes that the user has not approved committing or excluding.
- A deployment or data-safety blocker requires user action, such as missing prod env file, unavailable runner credentials, failed backup, or unclear target overwrite confirmation.

Final handoff must include:

- Changed files.
- Commits/PRs created or updated.
- Verification commands and results.
- UAT workflow run ID and deployed SHA if deployed.
- Whether UAT/prod/dev data was preserved, untouched, or explicitly refreshed.
- Remaining manual prerequisites for comprehensive UAT.
