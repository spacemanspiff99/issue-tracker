---
name: uat-gate
description: Use before saying "ready for UAT", "release-ready", "done" on a sprint, or asking the owner to test; and when working sprint 0007/0008 or issues 0008–0012 (local manual UAT readiness). Covers the Local Manual UAT readiness gate and where evidence is recorded.
---

# UAT Gate

Current objective (sprints 0007/0008, status planned): make the MVP ready for local manual UAT.
Issues: 0008 runtime gate → 0009 web UAT script → 0010 demo data/reset → 0011 MCP smoke →
0012 findings + release decision. Read the issue you're on, not the whole sprint doc.

## Gate (all on the same commit; record SHA)

1. Fresh image: `docker compose -f deployment/docker-compose.local.yml build`
2. Explicit migration on a fresh volume: `... run --rm app alembic upgrade head`
3. `... run --rm app python -m ruff check .` and `... run --rm app python -m pytest tests/`
4. `... up -d`, then `curl -fsS http://localhost:8000/health` → `"database": "ok"`
5. `RUN_BROWSER_UAT=1 ... pytest tests/e2e/`: full `ui-playwright` workflow catalog, desktop and
   mobile, screenshot per step, all green. A human click-through supplements this, never replaces it.
6. MCP: `... run --rm app python -m issue_tracker.mcp.server --smoke` (names only) plus
   `tests/integration/test_mcp_tools.py` (behavior).
7. Notes from `documentation/uat/TEMPLATE-local-uat.md` saved under `documentation/uat/` and
   linked from issue 0012.

Without Docker (cloud container): steps 2–6 can run against local Postgres per `schema-change`;
say explicitly that the image build/compose path was not exercised.

## Verdict

`PASS` only if every step passed on that SHA. Otherwise `BLOCKED: <step> — <evidence> — <next
action>`. Never upgrade a partial run to "ready".
