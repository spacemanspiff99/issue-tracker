# Backup, Export, And Restore Guide

Generated exports and backups belong in ignored `exports/` and `backups/` folders.

## Portable Recovery Bundle

Use recovery bundles for sanitized, inspectable project recovery. A bundle is an open directory of JSON, JSONL, Markdown-friendly metadata, checksums, app version, source commit, and Alembic revision. It includes tracker project data plus Guidance Sync sources, snapshots, drift, proposals, runs, ingested events, and audit summaries.

It excludes secrets, password hashes, sessions, environment files, raw audio, screenshots, local HTTPS certificates, database dumps, and generated cache files. That makes it suitable for later reviewable publication to `vibecoding`.

Create and verify a bundle:

```bash
docker compose -f deployment/docker-compose.local.yml run --rm app issue-tracker export-recovery-bundle 1 exports/recovery-bundles/issue-tracker/latest
docker compose -f deployment/docker-compose.local.yml run --rm app issue-tracker restore-recovery-bundle exports/recovery-bundles/issue-tracker/latest --dry-run
```

The dry run validates the manifest checksums and reports what would be created before any restore mutation exists.

## Legacy JSON Export

Export one project to JSON:

```bash
docker compose -f deployment/docker-compose.local.yml run --rm app issue-tracker export-json 1 exports/project-1.json
```

The export includes project data, categories, issues, dependencies, sprints, sprint membership, issue logs, and linked PR metadata. It does not include secrets, sessions, password hashes, or environment values.

Import requires an explicit target project and category mapping when source categories are present:

```bash
docker compose -f deployment/docker-compose.local.yml run --rm app issue-tracker import-json exports/project-1.json Restored --category-map IT-1=IT-1
```

## Raw Database And Artifact Backups

Database backup and restore should use PostgreSQL-native tools outside the app container. Keep dumps under `backups/` and do not commit them.

Raw audio, screenshots, local certs, and database dumps are not Git-safe. Back them up through encrypted provider-neutral tooling such as `restic`, `borg`, or `rclone`.

The app exposes a provider-neutral artifact backup adapter that records archive metadata and owner-action blockers without storing raw artifact contents in Issue Tracker. Missing external tools or credentials must stay blocked until a human installs and authenticates the chosen backend.

For `restic`, the expected owner-provided environment is:

```bash
export RESTIC_REPOSITORY=s3:s3.example.com/bucket/path
export RESTIC_PASSWORD=replace-with-secret
```

Do not commit these values. Store only the resulting archive IDs, checksums, and verification notes in tracker records or recovery manifests.

## Production-To-UAT Or Dev Data Refresh

Refreshing lower environments from production is not a deploy. It is a separate, explicit, backup-first operation for realistic testing.

Minimum safe workflow:

1. Confirm source `prod` and target `uat` or `dev`.
2. Get explicit user confirmation that the named target database will be overwritten.
3. Take a production dump without changing production data.
4. Take and verify a target backup before restore.
5. Restore the production dump into the target database only.
6. Do not copy production `.env` files, secrets, tokens, SSH keys, runtime config, or certificates.
7. Expire or remove restored sessions and use target-only admin setup or password reset steps. Password hashes and app tokens are not automatically sanitized yet, so treat this as a required manual post-restore step until an automated sanitizer exists.
8. Run `alembic upgrade head`, target `/health`, MCP smoke, and route/browser UAT checks.
9. Record the source dump identity, target backup path, command summary, post-restore SHA, and verification results in `documentation/uat/`.

Never copy UAT or dev data upward into production. Production restore is a different operation and requires an explicit request naming the production backup.

## Vibecoding Sanitized Backup Target

`vibecoding` can hold Git-safe recovery bundles under:

```text
projects/<project>/tracker-backups/latest/
projects/<project>/tracker-backups/snapshots/YYYY-MM-DD/
```

Publication requires `VIBECODING_MIRROR_TOKEN` and repository access. Without that token, the workflow must report a blocked owner action. Only sanitized bundle files and `publication-provenance.json` belong in this target; database dumps, raw audio, screenshots, certs, `.env` files, and generated exports must stay out of Git.
