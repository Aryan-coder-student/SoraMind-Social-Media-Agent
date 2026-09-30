"""Tests for the SQLite database connection backend."""

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool, StaticPool

from app.database.base import DatabaseConnection
from app.database.connections.sqlite import SQLiteConnection
from app.database.schemas.page import PageRow
from app.settings import (
    SQLALCHEMY_MAX_OVERFLOW,
    SQLALCHEMY_POOL_SIZE,
    SQLALCHEMY_POOL_TIMEOUT,
    SQLITE_DATABASE_URL,
)


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
    assert set(inspect(connection.connect()).get_table_names()) == {
        "page_versions",
        "pages",
        "section_versions",
    }


def test_create_tables_connects_lazily() -> None:
    database = SQLiteConnection("sqlite:///:memory:")

    try:
        database.create_tables()
        assert set(inspect(database.connect()).get_table_names()) == {
            "page_versions",
            "pages",
            "section_versions",
        }
    finally:
        database.close()


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
    engine = connection.connect()

    with engine.connect() as engine_connection:
        foreign_keys_enabled = engine_connection.exec_driver_sql(
            "PRAGMA foreign_keys"
        ).scalar_one()

    assert foreign_keys_enabled == 1


def test_in_memory_database_uses_one_shared_connection() -> None:
    database = SQLiteConnection("sqlite:///:memory:")

    try:
        engine = database.connect()
        assert isinstance(engine.pool, StaticPool)
    finally:
        database.close()



def test_file_database_uses_queue_pool(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'pool.db'}"
    database = SQLiteConnection(database_url)

    try:
        engine = database.connect()

        assert isinstance(engine.pool, QueuePool)
        assert engine.pool.size() == SQLALCHEMY_POOL_SIZE
        assert SQLALCHEMY_MAX_OVERFLOW == 5
        assert SQLALCHEMY_POOL_TIMEOUT == 30.0
    finally:
        database.close()


def test_file_database_reuses_checked_in_connection(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'reuse.db'}"
    database = SQLiteConnection(database_url)

    try:
        engine = database.connect()

        with engine.connect() as first_connection:
            first_driver_connection = first_connection.connection.driver_connection

        with engine.connect() as second_connection:
            second_driver_connection = second_connection.connection.driver_connection
    finally:
        database.close()

    assert first_driver_connection is second_driver_connection


def test_multiple_sessions_share_in_memory_database(
    connection: SQLiteConnection,
) -> None:
    session_factory = connection.create_session_factory()

    with session_factory() as first_session:
        first_session.add(
            PageRow(
                url="https://soraminds.com/about/",
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


def test_close_allows_a_fresh_connection() -> None:
    database = SQLiteConnection("sqlite:///:memory:")

    first_engine = database.connect()
    database.close()

    try:
        second_engine = database.connect()
    finally:
        database.close()

    assert first_engine is not second_engine


def test_default_database_url_uses_sqlite() -> None:
    assert SQLITE_DATABASE_URL.startswith("sqlite:///")


def test_connect_returns_sqlalchemy_engine() -> None:
    database = SQLiteConnection("sqlite:///:memory:")

    try:
        engine = database.connect()
        assert isinstance(engine, Engine)
    finally:
        database.close()
