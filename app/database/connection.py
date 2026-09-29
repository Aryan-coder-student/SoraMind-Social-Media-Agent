"""Synchronous SQLAlchemy setup for Phase 1 SQLite persistence."""

import sqlite3
from typing import Any

from sqlalchemy import Engine, event
from sqlalchemy import create_engine as sqlalchemy_create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.schema import Base

DEFAULT_DATABASE_URL = "sqlite:///./soramind.db"
IN_MEMORY_DATABASE_URLS = {
    "sqlite://",
    "sqlite:///:memory:",
}


def create_database_engine(
    database_url: str = DEFAULT_DATABASE_URL,
) -> Engine:
    """Create a synchronous engine configured for SQLite when applicable."""
    engine_options: dict[str, Any] = {}

    if database_url.startswith("sqlite:"):
        engine_options["connect_args"] = {"check_same_thread": False}

    if database_url in IN_MEMORY_DATABASE_URLS:
        engine_options["poolclass"] = StaticPool

    engine = sqlalchemy_create_engine(database_url, **engine_options)

    if engine.dialect.name == "sqlite":
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a reusable factory for synchronous database sessions."""
    return sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )


def create_tables(engine: Engine) -> None:
    """Create the current-state page and section tables."""
    Base.metadata.create_all(engine)


def _enable_sqlite_foreign_keys(
    dbapi_connection: sqlite3.Connection,
    _: object,
) -> None:
    """Enable SQLite foreign-key constraints for every new connection."""
    cursor = dbapi_connection.cursor()

    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()
