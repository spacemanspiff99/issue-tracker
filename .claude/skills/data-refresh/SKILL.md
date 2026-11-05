---
name: data-refresh
description: Destructive environment data refresh (prod->uat, prod->dev, or the approved dev->uat staging seed). Use when the user asks to copy, seed, refresh, or restore data between environments. Never used for production restores or upward copies.
disable-model-invocation: true
---

# Environment Data Refresh (Destructive to Target)

Source of truth: `documentation/guides/deployment.md` (Production-To-UAT Or Dev Data Refresh), `documentation/guides/backup-restore.md`, and `AGENTS.md`. Deep-tier work: use Opus at high effort.

## Allowed directions

| Source | Target | Allowed |
|---|---|---|
| prod | uat or dev | yes |
| dev | uat | only while there is no production data and the user has chosen UAT as staging |
| uat or dev | prod | **never** |
| anything | prod (restore) | only on a separate explicit request naming the production backup; this skill does not cover it |

## Procedure

1. **Plan in the tracker first.** Make sure a sprint or issue exists with pass/fail AC for this refresh. Create it if missing.
2. **Name everything explicitly:** source env and host, target env and host, target database name, operator, date.
3. **Back up both sides and verify the backups.**
   - Source: `pg_dump` (read-only on source). Record the file, size, and checksum.
   - Target: a pre-refresh backup under `backups/`. Confirm it is non-empty and that `pg_restore --list` succeeds.
   - If either backup fails, STOP.
4. **Hard confirmation gate.** Ask exactly this and stop:

   `STOP: I am about to overwrite <target> from <source>. Reply CONFIRM OVERWRITE <target> to proceed.`

   Continue only if the user's **latest** message contains that exact target-specific phrase. "ok", "continue", "go", "credentials ready", or approval of earlier steps does not count. Resolving a blocker (SSH, auth) authorizes only retrying the blocked non-destructive step.
5. **Restore to the target only.** Production stays unchanged. The project guard hook blocks destructive SQL and `pg_restore --clean` from Claude's shell. Give the user the exact restore command to run, or ask them to approve running it outside the guard. Never try to get around the hook.
6. **Sanitize.** Expire sessions. Treat password hashes, tokens, and remembered logins as sensitive. Do target-only admin setup or a password reset if needed.
7. **Verify the target:** `alembic upgrade head`, `/health` (DB connected), MCP smoke, route checks, browser or manual UAT, and representative data counts compared with the source.
8. **Record evidence** in the tracker and in a `documentation/uat/` note: source dump identity, target backup path, hosts, DB name, operator, date, post-restore commit SHA, and pass/fail per check.
