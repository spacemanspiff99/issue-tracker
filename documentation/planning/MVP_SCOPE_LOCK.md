# MVP Scope Lock

This document records the original MVP boundary. Later dogfood sprints have added post-MVP capabilities such as backlog ordering, release planning, voice intake, and Guidance Sync; keep those documented in the product guide and sprint closeout notes instead of retroactively widening this MVP lock.

## In Scope

- Single-user FastAPI/Jinja web app.
- PostgreSQL persistence through SQLAlchemy and Alembic.
- Project-scoped categories, issue logs, dependencies, sprints, and shared `NNNN` issue/sprint IDs.
- Required acceptance criteria on every issue.
- Immutable close metadata with originating LLM.
- Compact stdio MCP tools backed by the same services as web routes.
- Explicit migrations, Docker Compose local runtime, JSON import/export, and backup guidance.

## Out Of Scope

- React or Next.js.
- Full GitHub issue synchronization.
- Automatic full markdown tracker migration.
- Drag-and-drop planning UI.
- Multi-user roles.
- Background schedulers beyond health and one-off commands.

Non-MVP requests should be recorded as backlog rather than folded into the active MVP.
