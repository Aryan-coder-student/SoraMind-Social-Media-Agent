"""SQLite connection backend for Phase 1 persistence."""

import sqlite3
from typing import Any

from sqlalchemy import Engine, event
from sqlalchemy import create_engine as sqlalchemy_create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool, StaticPool

from app.database.base import DatabaseConnection
from app.database.schemas import Base
from app.settings import (
    SQLALCHEMY_MAX_OVERFLOW,
    SQLALCHEMY_POOL_SIZE,
    SQLALCHEMY_POOL_TIMEOUT,
    SQLITE_DATABASE_URL,
)


class SQLiteConnection(DatabaseConnection):
    """Own SQLite engine lifecycle and SQLAlchemy session/table setup."""

    def __init__(self, database_url: str = SQLITE_DATABASE_URL) -> None:
        self.database_url = database_url
        self._engine: Engine | None = None

    def connect(self) -> Engine:
        """Create the SQLite engine once and return it."""
        if self._engine is None:
            self._engine = self._create_engine()

        return self._engine

    def create_session_factory(self) -> sessionmaker[Session]:
        """Create a reusable synchronous session factory."""
        return sessionmaker(
            bind=self.connect(),
            autoflush=False,
            expire_on_commit=False,
        )

    def create_tables(self) -> None:
        """Create the SQLAlchemy tables for the configured SQLite database."""
        Base.metadata.create_all(self.connect())

    def close(self) -> None:
        """Dispose the active engine."""
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None

    def _create_engine(self) -> Engine:
        """Build an engine using only SQLite-specific configuration."""
        engine = sqlalchemy_create_engine(
            self.database_url,
            **self._engine_options(),
        )
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)
        return engine

    def _engine_options(self) -> dict[str, Any]:
        """Return SQLite engine options for the configured database URL."""
        options: dict[str, Any] = {
            "connect_args": {"check_same_thread": False},
        }

        if _is_in_memory_database(self.database_url):
            # An in-memory SQLite database belongs to one DB-API connection.
            # StaticPool keeps all sessions on that same connection.
            options["poolclass"] = StaticPool
        else:
            options.update(
                {
                    "poolclass": QueuePool,
                    "pool_size": SQLALCHEMY_POOL_SIZE,
                    "max_overflow": SQLALCHEMY_MAX_OVERFLOW,
                    "pool_timeout": SQLALCHEMY_POOL_TIMEOUT,
                }
            )

        return options


def _is_in_memory_database(database_url: str) -> bool:
    """Return whether the URL represents an in-memory SQLite database."""
    return database_url in {
        "sqlite://",
        "sqlite:///:memory:",
    }


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
