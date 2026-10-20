"""Compare the migrated database schema with SQLAlchemy models (IT-3).

Usage: DATABASE_URL=postgresql+psycopg://... python .claude/skills/schema-change/schema_drift.py
Run after `alembic upgrade head` on an empty database. Exit 1 when drift exists.
"""

from __future__ import annotations

import os
import sys

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

from issue_tracker.domain.models import Base


def describe(diff: object) -> str:
    op = diff[0] if isinstance(diff, list) else diff
    kind = op[0]
    if kind in {"add_table", "remove_table"}:
        return f"{kind}: {op[1].name}"
    if kind in {"add_column", "remove_column"}:
        return f"{kind}: {op[2]}.{op[3].name}"
    if kind.startswith("modify_"):
        return f"{kind}: {op[2]}.{op[3]} {op[5]} -> {op[6]}"
    return f"{kind}: {op[1]}"


def main() -> int:
    engine = create_engine(os.environ["DATABASE_URL"])
    with engine.connect() as conn:
        diffs = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    for diff in diffs:
        print(describe(diff))
    print(f"{len(diffs)} difference(s) between migrations and models")
    return 1 if diffs else 0


if __name__ == "__main__":
    sys.exit(main())
