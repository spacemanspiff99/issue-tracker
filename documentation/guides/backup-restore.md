# Backup, Export, And Restore Guide

Generated exports and backups belong in ignored `exports/` and `backups/` folders.

Export one project to JSON:

```bash
docker compose -f deployment/docker-compose.local.yml run --rm app issue-tracker export-json 1 exports/project-1.json
```

The export includes project data, categories, issues, dependencies, sprints, sprint membership, issue logs, and linked PR metadata. It does not include secrets, sessions, password hashes, or environment values.

Import requires an explicit target project and category mapping when source categories are present:

```bash
docker compose -f deployment/docker-compose.local.yml run --rm app issue-tracker import-json exports/project-1.json Restored --category-map IT-1=IT-1
```

Database backup and restore should use PostgreSQL-native tools outside the app container. Keep dumps under `backups/` and do not commit them.
