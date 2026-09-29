"""SQLite connection backend for Phase 1 persistence."""

import sqlite3
from typing import Any

from sqlalchemy import Engine, event
from sqlalchemy import create_engine as sqlalchemy_create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import DatabaseConnection
from app.database.schemas.sqlalchemy import Base

DEFAULT_DATABASE_URL = "sqlite:///./soramind.db"
IN_MEMORY_DATABASE_URLS = {
    "sqlite://",
    "sqlite:///:memory:",
}


class SQLiteConnection(DatabaseConnection):
    """Own SQLite engine lifecycle and SQLAlchemy session/table setup."""

    def __init__(self, database_url: str = DEFAULT_DATABASE_URL) -> None:
        self.database_url = database_url
        self._engine: Engine | None = None

    @property
    def engine(self) -> Engine:
        """Return the active engine, requiring connect() first."""
        if self._engine is None:
            raise RuntimeError("SQLite connection has not been opened")
        return self._engine

    def connect(self) -> Engine:
        """Create the SQLite engine once and return it."""
        if self._engine is not None:
            return self._engine

        engine_options: dict[str, Any] = {
            "connect_args": {"check_same_thread": False},
        }

        if self.database_url in IN_MEMORY_DATABASE_URLS:
            engine_options["poolclass"] = StaticPool

        engine = sqlalchemy_create_engine(
            self.database_url,
            **engine_options,
        )
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)
        self._engine = engine
        return engine

    def create_session_factory(self) -> sessionmaker[Session]:
        """Create a reusable synchronous session factory."""
        return sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
        )

    def create_tables(self) -> None:
        """Create the SQLAlchemy tables for the active SQLite engine."""
        Base.metadata.create_all(self.engine)

    def close(self) -> None:
        """Dispose the active engine."""
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None


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
