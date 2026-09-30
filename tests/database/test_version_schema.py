"""Schema tests for immutable page and section version snapshots."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import delete, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.database.connections.sqlite import SQLiteConnection
from app.database.schemas.sqlalchemy import PageRow, PageVersionRow, SectionVersionRow


@pytest.fixture
def database() -> SQLiteConnection:
    connection = SQLiteConnection("sqlite:///:memory:")
    connection.connect()
    connection.create_tables()
    yield connection
    connection.close()


@pytest.fixture
def session_factory(database: SQLiteConnection) -> sessionmaker[Session]:
    return database.create_session_factory()


def make_page() -> PageRow:
    return PageRow(url="https://soraminds.com/about/")


def make_version(version_number: int) -> PageVersionRow:
    return PageVersionRow(
        version_number=version_number,
        title=f"Version {version_number}",
        fingerprint=str(version_number) * 64,
        captured_at=datetime.now(UTC),
        sections=[
            SectionVersionRow(
                section_index=0,
                text=f"Snapshot {version_number}",
                fingerprint=str(version_number) * 64,
            )
        ],
    )


def test_creates_identity_and_version_tables(database: SQLiteConnection) -> None:
    assert set(inspect(database.connect()).get_table_names()) == {
        "pages",
        "page_versions",
        "section_versions",
    }


def test_page_is_active_by_default(session_factory: sessionmaker[Session]) -> None:
    page = make_page()

    with session_factory() as session:
        session.add(page)
        session.commit()

    assert page.is_active is True
    assert page.current_version_id is None


def test_page_can_point_to_current_version(
    session_factory: sessionmaker[Session],
) -> None:
    page = make_page()

    with session_factory() as session:
        session.add(page)
        session.flush()
        version = make_version(1)
        page.versions.append(version)
        session.flush()
        page.current_version_id = version.id
        session.commit()
        page_id = page.id
        version_id = version.id

    with session_factory() as session:
        stored_page = session.get(PageRow, page_id)

    assert stored_page is not None
    assert stored_page.current_version_id == version_id


def test_page_version_numbers_are_unique_per_page(
    session_factory: sessionmaker[Session],
) -> None:
    page = make_page()
    page.versions.extend([make_version(1), make_version(1)])

    with session_factory() as session:
        session.add(page)
        with pytest.raises(IntegrityError):
            session.commit()


def test_version_relationships_are_ordered(
    session_factory: sessionmaker[Session],
) -> None:
    page = make_page()
    later = make_version(2)
    later.sections.extend(
        [
            SectionVersionRow(
                section_index=2,
                text="Third",
                fingerprint="c" * 64,
            ),
            SectionVersionRow(
                section_index=1,
                text="Second",
                fingerprint="b" * 64,
            ),
        ]
    )
    page.versions.extend([later, make_version(1)])

    with session_factory() as session:
        session.add(page)
        session.commit()
        page_id = page.id

    with session_factory() as session:
        stored_page = session.get(PageRow, page_id)
        assert stored_page is not None
        assert [item.version_number for item in stored_page.versions] == [1, 2]
        assert [
            item.section_index
            for item in stored_page.versions[1].sections
        ] == [0, 1, 2]


def test_deleting_page_cascades_to_all_version_rows(
    session_factory: sessionmaker[Session],
) -> None:
    page = make_page()

    with session_factory() as session:
        session.add(page)
        session.flush()
        version = make_version(1)
        page.versions.append(version)
        session.flush()
        page.current_version_id = version.id
        session.commit()

        page_id = page.id
        version_id = version.id
        section_version_id = version.sections[0].id

        session.execute(delete(PageRow).where(PageRow.id == page_id))
        session.commit()

    with session_factory() as session:
        assert session.get(PageVersionRow, version_id) is None
        assert session.get(SectionVersionRow, section_version_id) is None


def test_version_foreign_keys_have_indexes(database: SQLiteConnection) -> None:
    engine = database.connect()
    page_indexes = {
        tuple(item["column_names"])
        for item in inspect(engine).get_indexes("page_versions")
    }
    section_indexes = {
        tuple(item["column_names"])
        for item in inspect(engine).get_indexes("section_versions")
    }

    assert ("page_id",) in page_indexes
    assert ("page_version_id",) in section_indexes
