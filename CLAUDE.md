# Claude Code Project Memory

Shared project rules live in `AGENTS.md` and are imported here. This file holds only Claude Code specifics.

@AGENTS.md

## Claude Code Specifics

### Commands (Docker-only)

Normal development runs in Docker/Compose. Do not use host Python, host virtualenvs, host PostgreSQL, or host Alembic.

```bash
DC="docker compose -f deployment/docker-compose.local.yml"
$DC run --rm app python -m pytest tests/                    # test gate
$DC run --rm app python -m pytest tests/unit -q             # fast loop
$DC run --rm app ruff check src tests                       # lint
$DC run --rm app alembic upgrade head                       # explicit migration
$DC run --rm app python -m issue_tracker.mcp.server --smoke # MCP smoke
$DC config                                                  # compose sanity
```

Run browser and Playwright tests inside the image or app container only (see `documentation/guides/local-development.md`).

`tests/conftest.py` runs `drop_all`/`create_all` against `TEST_DATABASE_URL`, which defaults to in-memory SQLite. Never point `TEST_DATABASE_URL` at the dev, UAT, or prod database. For PostgreSQL-backed tests, use a throwaway database or a compose project with a unique `COMPOSE_PROJECT_NAME`.

### Model Mapping

`AGENTS.md` defines the reasoning tiers. In Claude Code:

- `standard`: Sonnet, or Opus at default effort, for routine implementation, tests, docs, and focused route/service changes.
- `deep`: Opus at high effort for schema/migration, auth/secrets, deployment, MCP contracts, UAT/release decisions, difficult debugging, and anything that can corrupt tracker state.
- Subagents: Haiku or Sonnet only for bounded read-only searches or mechanical edits. Use Opus for `deep`-tier subtasks. Parallel subagents must have disjoint write scopes.
- When an issue or prompt names a GPT model, map it to the matching tier above. Do not log it as a model mismatch.

### Tracker Access

- `.mcp.json` registers the `issue-tracker` stdio MCP server through the local compose stack. It uses the dev database; `docker compose run` starts the dev `postgres` service if it is not running (it never recreates the volume). Use it to check the active issue or sprint before starting work and to record status and evidence at closeout (see the dual-tracker rules in `AGENTS.md`).
- If the MCP server is unavailable, say so and fall back to the web UI or CLI. Do not skip the tracker check without telling the user.

### Skills

Use these project skills for high-risk or repeated workflows rather than improvising:

- `/uat-deploy`: source-of-truth gate, dry run, and SHA-pinned local UAT deploy on the dev host (`deployment/scripts/local-uat-deploy.sh`). There is no production path until issue `0178` (k3s).
- `/data-refresh`: destructive prod->uat/dev or dev->uat data refresh with the exact `CONFIRM OVERWRITE <target>` gate.
- `/local-uat-preflight`: fresh build, migration, tests, `/health`, browser UAT, and Docker cleanup without disturbing the live dev app.
- `/sprint-closeout`: tracker and markdown reconciliation, AC/IT checklist, evidence, and STOP handoff.

### Enforced Guards

`.claude/settings.json` denies or asks before destructive commands, including volume removal, broad prune, `alembic downgrade`, force-push, `git reset --hard`, host Playwright installs, and `sudo`. A denied command is a STOP signal: explain the situation and ask the user. Never work around a guard.

### Git

- Branch from `dev` and open PRs into `dev`. Promote `dev` to `main` only by PR, and only when asked.
- Commit or push only when the user asks.
