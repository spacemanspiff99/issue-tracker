---
name: guidance-change
description: Use before editing `CLAUDE.md`, `.claude/README.md`, any `.claude/rules/*.md`, `.claude/skills/*`, or `.claude/settings.json`, or when porting a rule from another project's guidance (e.g. weather-app via vibecoding). Covers placement (core vs rule vs skill), token budget, cross-reference checks, and the vibecoding mirror.
---

# Guidance Change

## Placement — pick the cheapest layer that still fires

| Layer | Loads | Put here |
| --- | --- | --- |
| `CLAUDE.md` | every session | facts needed every session; one-line tripwires whose miss is costly; skill index |
| `.claude/rules/*.md` (`paths:`) | when matching files are touched | short invariants for that code area |
| `.claude/skills/*/SKILL.md` | when the description matches the task | procedures, commands, checklists |
| `documentation/` | on demand | long reference |

Budget: `CLAUDE.md` ≤ ~110 lines; a rule ≤ 20 lines; a skill ≤ ~80 lines. Say it once — point
to the owner instead of repeating. Skill `description` is always injected: keep it to the
triggers.

## Steps

1. Draft the change; state which layer and why.
2. Every name/path/command you cite must exist: Grep each skill name, file path, and test name.
   Run any command you add.
3. Adding/removing/renaming a skill → update the `CLAUDE.md` skill index and `.claude/README.md`.
4. Porting from another project: take the principle, not its hosts/branches/trackers
   (weather-app's Linear, `dev→prod`, `WEA-` tokens, LAN hosts don't apply here).
5. Don't edit `AGENTS.md`, `.codex/`, `.cursor/` unless asked; never edit the vibecoding mirror.

The mirror (`.github/workflows/mirror-rules.yml`) publishes `CLAUDE.md` and `.claude/` to
`vibecoding/projects/issue-tracker/claude-guidance/` on push to `main`.
