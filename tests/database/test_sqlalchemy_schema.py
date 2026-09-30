"""Tests for the relational SQLAlchemy Company Knowledge page identity schema."""

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.database.connections.sqlite import SQLiteConnection
from app.database.schemas.sqlalchemy import PageRow


@pytest.fixture
def connection() -> SQLiteConnection:
    database = SQLiteConnection("sqlite:///:memory:")
    database.connect()
    database.create_tables()
    yield database
    database.close()


@pytest.fixture
def session_factory(
    connection: SQLiteConnection,
) -> sessionmaker[Session]:
    return connection.create_session_factory()


def make_page(
    *,
    url: str = "https://soraminds.com/about/",
) -> PageRow:
    return PageRow(url=url)


def test_page_stores_identity_and_lifecycle_only(
    connection: SQLiteConnection,
) -> None:
    columns = {
        column["name"]
        for column in inspect(connection.connect()).get_columns("pages")
    }

    assert columns == {
        "id",
        "url",
        "is_active",
        "current_version_id",
    }


def test_page_url_must_be_unique(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        session.add_all([make_page(), make_page()])

        with pytest.raises(IntegrityError):
            session.commit()


def test_current_version_id_references_page_versions(
    connection: SQLiteConnection,
) -> None:
    foreign_keys = inspect(connection.connect()).get_foreign_keys("pages")

    assert any(
        key["constrained_columns"] == ["current_version_id"]
        and key["referred_table"] == "page_versions"
        for key in foreign_keys
    )


def test_page_identity_has_no_duplicate_current_content_columns(
    connection: SQLiteConnection,
) -> None:
    columns = {
        column["name"]
        for column in inspect(connection.connect()).get_columns("pages")
    }

    assert "title" not in columns
    assert "meta_description" not in columns
    assert "canonical_url" not in columns
    assert "fingerprint" not in columns
