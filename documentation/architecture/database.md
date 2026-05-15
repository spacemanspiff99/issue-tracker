# Database Architecture

The MVP uses one central Alembic migration tree in `migrations/` and SQLAlchemy 2.x mappings in `src/issue_tracker/domain/models.py`.

Core invariants:

- Projects allocate one shared local sequence for issues and sprints. Display IDs are four-digit values such as `0001`.
- Issues require acceptance criteria before creation.
- Categories are project-scoped records. Peer project taxonomy names are never application constants.
- Dependencies reject self-edges in the database and cycles in the service layer.
- Closing an issue stores immutable close metadata: closed timestamp, originating LLM, actor, and close note.
- Migrations are explicit. App startup does not drop, recreate, truncate, or silently migrate a database.

Validation:

```bash
docker compose -f deployment/docker-compose.local.yml run --rm app alembic upgrade head
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/unit tests/integration
```
