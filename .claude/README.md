# Claude Code Guidance

Entry point: [`../CLAUDE.md`](../CLAUDE.md). Adapted from the weather-app three-layer design
(mirrored in `spacemanspiff99/vibecoding` under `weather-app/claude-guidance/`), cut down for a
small single-branch project: no Linear, no session tags, no branch-integration reviewer. Hosts:
dev `.20` → UAT `.18` → production `192.168.10.8`.

| Layer | Path | Loads |
| --- | --- | --- |
| Core | `../CLAUDE.md` | every session (~90 lines) |
| Rules | [`rules/`](rules/) — `services`, `migrations`, `mcp`, `web`, `deployment` | when a file matching the rule's `paths:` is touched |
| Skills | [`skills/`](skills/) — `schema-change`, `tracker-invariants`, `mcp-contract`, `web-auth`, `deploy-safety`, `ui-playwright`, `tracker-docs`, `uat-gate`, `guidance-change` | when the task matches the skill `description` |
| Reference | `../documentation/` | on demand |

Rules hold short invariants; skills hold procedures and commands. Each `IT-n` category from
`documentation/standards/ISSUE_LOG.md` has one owning rule + skill:
IT-1/IT-2 `services` + `tracker-invariants`, IT-3 `migrations` + `schema-change`,
IT-4 `mcp` + `mcp-contract`, IT-5 `web` + `web-auth`, IT-6 `deployment` + `deploy-safety`.

[`settings.json`](settings.json) pre-approves read-only and test commands only.

Codex (`AGENTS.md`, `.codex/`) and Cursor (`.cursor/`) guidance is separate and not maintained
from Claude sessions. Edits here follow the `guidance-change` skill.
