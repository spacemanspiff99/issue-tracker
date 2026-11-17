from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from issue_tracker.domain.models import Base


def _assert_disposable_test_database(url: str) -> None:
    """Refuse to drop_all on anything but SQLite or a database whose name ends in _test."""
    from sqlalchemy.engine import make_url

    parsed = make_url(url)
    if parsed.get_backend_name() == "sqlite":
        return
    if not (parsed.database or "").endswith("_test"):
        raise pytest.UsageError(
            f"TEST_DATABASE_URL database {parsed.database!r} does not end in '_test'; "
            "tests drop_all. Use the postgres-test compose service."
        )


@pytest.fixture()
def engine():
    url = os.environ.get("TEST_DATABASE_URL", "sqlite+pysqlite:///:memory:")
    _assert_disposable_test_database(url)
    kwargs = {"pool_pre_ping": True}
    if url == "sqlite+pysqlite:///:memory:":
        kwargs["connect_args"] = {"check_same_thread": False}
        kwargs["poolclass"] = StaticPool
    engine = create_engine(url, **kwargs)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def session(engine) -> Iterator[Session]:
    maker = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with maker() as session:
        yield session
