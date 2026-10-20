---
paths:
  - "migrations/**"
  - "alembic.ini"
  - "src/issue_tracker/domain/models.py"
---

# Schema invariants (IT-3)

- `migrations/versions/` is the only migration tree. Revision ids are `NNNN_snake_name`;
  `down_revision` must point at the current head.
- Models and migrations must agree. Known drift: `0002_guidance_sync` and
  `0003_guidance_audit_events` create `guidance_*` tables that have no model in `models.py`.
  Don't widen it; don't "fix" it silently inside an unrelated change.
- Forward-only in releases. No drop/truncate/data-destroying op without an explicit,
  user-approved data disposition.
- Unit tests build schema with `create_all`, so they cannot catch migration bugs — run the
  Postgres check in the `schema-change` skill.
