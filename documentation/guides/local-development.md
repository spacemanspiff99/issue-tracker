# Local Development Guide

Prerequisites are Docker, Docker Compose, and Git. Normal setup does not require host `pip install`, a host virtualenv, host PostgreSQL, or host Alembic.

Start from a checkout:

```bash
git clone https://github.com/spacemanspiff99/issue-tracker.git
cd issue-tracker
docker compose -f deployment/docker-compose.local.yml build
docker compose -f deployment/docker-compose.local.yml run --rm app alembic upgrade head
docker compose -f deployment/docker-compose.local.yml up
```

Open `http://localhost:8000/setup` and create the admin account. Passwords are hashed with Argon2 and are never logged by the app.

Run checks:

```bash
docker compose -f deployment/docker-compose.local.yml run --rm app python -m pytest tests/
docker compose -f deployment/docker-compose.local.yml run --rm app python -m issue_tracker.mcp.server --smoke
docker compose -f deployment/docker-compose.local.yml config
```

Run one-off commands:

```bash
docker compose -f deployment/docker-compose.local.yml run --rm app issue-tracker export-json 1 exports/project-1.json
docker compose -f deployment/docker-compose.local.yml run --rm app issue-tracker import-json exports/project-1.json Imported --category-map IT-1=IT-1
```
