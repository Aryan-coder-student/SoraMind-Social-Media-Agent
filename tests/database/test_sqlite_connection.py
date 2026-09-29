"""Tests for the SQLite database connection backend."""

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.engine import Engine

from app.database.base import DatabaseConnection
from app.database.connections.sqlite import SQLiteConnection
from app.database.schemas.sqlalchemy import PageRow
from app.settings import SQLITE_DATABASE_URL


@pytest.fixture
def connection() -> SQLiteConnection:
    database = SQLiteConnection("sqlite:///:memory:")
    database.connect()
    database.create_tables()
    yield database
    database.close()


def test_sqlite_connection_implements_database_contract() -> None:
    assert isinstance(SQLiteConnection(), DatabaseConnection)


def test_creates_in_memory_sqlite_engine() -> None:
    database = SQLiteConnection("sqlite:///:memory:")

    try:
        engine = database.connect()
        assert engine.dialect.name == "sqlite"

        with engine.connect() as connection:
            assert connection.exec_driver_sql("SELECT 1").scalar_one() == 1
    finally:
        database.close()


def test_create_tables_creates_page_and_section_tables(
    connection: SQLiteConnection,
) -> None:
    assert set(inspect(connection.engine).get_table_names()) == {
        "pages",
        "sections",
    }


def test_session_factory_returns_configured_working_session(
    connection: SQLiteConnection,
) -> None:
    session_factory = connection.create_session_factory()

    with session_factory() as session:
        assert session.autoflush is False
        assert session.expire_on_commit is False
        assert session.scalar(select(1)) == 1


def test_enables_sqlite_foreign_keys(
    connection: SQLiteConnection,
) -> None:
    with connection.engine.connect() as engine_connection:
        foreign_keys_enabled = engine_connection.exec_driver_sql(
            "PRAGMA foreign_keys"
        ).scalar_one()

    assert foreign_keys_enabled == 1


def test_multiple_sessions_share_in_memory_database(
    connection: SQLiteConnection,
) -> None:
    session_factory = connection.create_session_factory()

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


def test_connect_reuses_active_engine() -> None:
    database = SQLiteConnection("sqlite:///:memory:")

    try:
        first_engine = database.connect()
        second_engine = database.connect()
    finally:
        database.close()

    assert first_engine is second_engine


def test_engine_requires_active_connection() -> None:
    database = SQLiteConnection("sqlite:///:memory:")

    with pytest.raises(RuntimeError, match="has not been opened"):
        _ = database.engine


def test_close_releases_engine() -> None:
    database = SQLiteConnection("sqlite:///:memory:")
    database.connect()
    database.close()

    with pytest.raises(RuntimeError, match="has not been opened"):
        _ = database.engine


def test_default_database_url_uses_sqlite() -> None:
    assert SQLITE_DATABASE_URL.startswith("sqlite:///")


def test_connect_returns_sqlalchemy_engine() -> None:
    database = SQLiteConnection("sqlite:///:memory:")

    try:
        engine = database.connect()
        assert isinstance(engine, Engine)
    finally:
        database.close()
