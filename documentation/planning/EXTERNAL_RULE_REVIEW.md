# External Rule Review For GPT-5.5 Work

Review date: 2026-05-14.

Sources examined:

- `https://github.com/spacemanspiff99?tab=repositories` through the GitHub public repositories API.
- `https://github.com/spacemanspiff99/handbrake2resilio` through public raw files and repository contents.
- `https://github.com/spacemanspiff99/vibecoding`; public API and unauthenticated clone returned 404/auth failure, so direct contents were not available in this environment.
- This repository's existing mirror workflow and planning references for `spacemanspiff99/vibecoding`.

Public repository inventory found:

| Repository | Relevant rule source | Finding |
|---|---|---|
| `issue-tracker` | `AGENTS.md`, `.cursor/rules/*.mdc` | Already contains the strongest project-specific architecture, schema, MCP, and mirror guidance. |
| `handbrake2resilio` | `AGENTS.md`, `.cursor/rules/agents.mdc`, `.cursor/rules/rules.mdc` | Strong process rules for prompt AC, model recommendation checks, evidence-first debugging, UI/browser verification, container discipline, and STOP handoffs. |
| `creative-outside` | public API says empty | No rules available. |
| `k3s-ha` | public API says empty | No rules available. |
| Cloud Run test/demo repos | root metadata only from repository list | No reusable project rules identified. |
| `zoneminder.machine.learning` | fork, old, no issue-tracker rule relevance | Not used. |

Rules adopted into this repo:

- GPT-5.5 `medium` is the default for normal implementation, tests, documentation, and focused route/service work.
- GPT-5.5 `high` is required for architecture, migrations, auth/secrets, deployment, MCP contracts, local manual UAT readiness, difficult debugging, and release decisions.
- Issues and prompts must state the recommended model/reasoning level and record any mismatch before work starts.
- Complex planning should use sequential role review: project manager, engineering manager, relevant implementation engineer, DevOps, and QA.
- Debugging should start from logs, runtime output, request/response bodies, and database state before code changes.
- UI-facing readiness needs browser or route-level proof that pages are styled and usable; no-JS-error checks alone are not enough.
- Local manual UAT readiness requires fresh container build, explicit migration, pytest, `/health` database check, setup/login, project/issue/dependency/sprint/close path, and a written notes location.

Rules intentionally not adopted:

- Handbrake-specific Linear project ownership, host paths, port numbers, deployment flow, and product taxonomy.
- Emoji markers and mandatory commit/push behavior after every prompt. This repo keeps Codex closeout evidence and user-controlled git operations instead.
- Any private or unavailable `vibecoding` content not visible through public GitHub access.
