"""Tests for synchronous SQLite engine and session setup."""

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.engine import Engine

from app.database.connection import (
    DEFAULT_DATABASE_URL,
    create_database_engine,
    create_session_factory,
    create_tables,
)
from app.database.schema import PageRow


@pytest.fixture
def engine() -> Engine:
    database_engine = create_database_engine("sqlite:///:memory:")
    create_tables(database_engine)
    yield database_engine
    database_engine.dispose()


def test_creates_in_memory_sqlite_engine() -> None:
    engine = create_database_engine("sqlite:///:memory:")

    try:
        assert engine.dialect.name == "sqlite"
        with engine.connect() as connection:
            assert connection.exec_driver_sql("SELECT 1").scalar_one() == 1
    finally:
        engine.dispose()


def test_creates_page_and_section_tables(engine: Engine) -> None:
    assert set(inspect(engine).get_table_names()) == {"pages", "sections"}


def test_session_factory_returns_configured_working_session(
    engine: Engine,
) -> None:
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        assert session.autoflush is False
        assert session.expire_on_commit is False
        assert session.scalar(select(1)) == 1


def test_enables_sqlite_foreign_keys(engine: Engine) -> None:
    with engine.connect() as connection:
        foreign_keys_enabled = connection.exec_driver_sql(
            "PRAGMA foreign_keys"
        ).scalar_one()

    assert foreign_keys_enabled == 1


def test_multiple_sessions_share_in_memory_database(engine: Engine) -> None:
    session_factory = create_session_factory(engine)

    with session_factory() as first_session:
        first_session.add(
            PageRow(
                url="https://soraminds.com/about/",
                fingerprint="a" * 64,
            )
        )
        first_session.commit()

    with session_factory() as second_session:
        stored_page = second_session.scalar(select(PageRow))

    assert stored_page is not None
    assert stored_page.url == "https://soraminds.com/about/"


def test_default_database_url_uses_sqlite() -> None:
    assert DEFAULT_DATABASE_URL.startswith("sqlite:///")
