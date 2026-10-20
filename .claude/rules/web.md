---
paths:
  - "src/issue_tracker/web/**"
  - "tests/integration/test_web_routes.py"
---

# Web invariants (IT-5)

- Routes validate form input, call one service method, render or redirect. No business rules in
  routes or templates.
- Server-rendered Jinja + HTML forms; minimal JS. No React/Next or frontend build step.
- Every page except `/health`, `/setup` (only while no user exists) and `/login` requires a session.
- Passwords hashed in `web/security.py` (Argon2); never log credentials or form bodies.
- Session cookie HTTP-only, SameSite=Lax, `Secure` from `SESSION_COOKIE_SECURE`.
- Procedure and verification: `web-auth` skill.
