# Issue Tracker Recurring Issue Log

This file owns the issue-tracker project's recurring bug taxonomy. Do not copy category content from weather-app, investments, storyteller, or any other peer project.

## Categories

| Category | Name | Prevention checklist |
|---|---|---|
| `IT-1` | Tracker State Integrity | Verify project-local sequence allocation, status transitions, dependency cycle rejection, and immutable close metadata. |
| `IT-2` | Category And AC Binding | Verify acceptance criteria are required, category checklists are inlined when applicable, and project taxonomies remain project-scoped data. |
| `IT-3` | Schema And Migration Safety | Verify SQLAlchemy models, PostgreSQL constraints, and Alembic migrations agree; run migration checks on an empty database. |
| `IT-4` | MCP Contract And Token Discipline | Verify tool schemas, compact default outputs, limit/filter parameters, opt-in detail, and stderr-only logging. |
| `IT-5` | Auth And Secret Safety | Verify password hashing, session flags, setup flow, secret handling, and no credential logging. |
| `IT-6` | Deployment And Configuration Drift | Verify compose files, env vars, health checks, explicit migrations, and workflow behavior stay aligned. |

## Log

| Date | Issue | Category | Root cause | Prevention added |
|---|---|---|---|---|
| 2026-04-24 | Initial taxonomy | n/a | New project rules need a project-owned category list. | Added `IT-1` through `IT-6` and wired them into `.cursor/rules/ac.mdc`. |
