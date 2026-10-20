---
name: web-auth
description: Use when changing FastAPI routes or Jinja templates in `src/issue_tracker/web/`, the setup/login/logout flow, sessions, password hashing, login rate limiting, or anything a user sees in the browser. Covers IT-5 (auth and secret safety), route-test and browser verification.
---

# Web and Auth (IT-5)

## Route pattern

`Form(...)` input → `require_user(request, session)` → one service call → `TemplateResponse` or
303 redirect. Catch `DomainError` and re-render the form with an inline error (no 500s for
user mistakes). Templates extend `base.html`; use the `display_id` global for `NNNN`.

## Auth rules

- `/setup` works only while `AuthService.setup_required()`; afterwards it must redirect.
- Argon2 via `web/security.py`; login limited after 5 failures (in-memory, per process).
- `SessionMiddleware`: `same_site="lax"`, `https_only` from `SESSION_COOKIE_SECURE`.
- Never log form bodies, passwords, `APP_SECRET_KEY`, or `DATABASE_URL` with credentials.

## Verify

1. Route tests in `tests/integration/test_web_routes.py` (TestClient): auth redirect, happy path,
   validation error path.
2. Visible change → browser check. Clean logs or a 200 are not proof the page is usable.
   Local: `docker compose -f deployment/docker-compose.local.yml up` then open
   `http://localhost:8000`. Cloud container: run uvicorn against a migrated Postgres
   (`schema-change` has the setup) and drive it with Playwright using
   `executablePath: '/opt/pw-browsers/chromium'`; capture one screenshot per changed page and say
   what it shows.
