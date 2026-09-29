"""Tests for the Company Knowledge database schema."""

import pytest
from sqlalchemy import delete, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.database.connection import (
    create_database_engine,
    create_session_factory,
    create_tables,
)
from app.database.schema import PageRow, SectionRow


@pytest.fixture
def engine() -> Engine:
    database_engine = create_database_engine("sqlite:///:memory:")
    create_tables(database_engine)
    yield database_engine
    database_engine.dispose()


@pytest.fixture
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return create_session_factory(engine)


def make_page(
    *,
    url: str = "https://soraminds.com/about/",
    title: str | None = "About SoraMinds",
    meta_description: str | None = "Learn about SoraMinds",
    canonical_url: str | None = "https://soraminds.com/about/",
    fingerprint: str = "a" * 64,
) -> PageRow:
    return PageRow(
        url=url,
        title=title,
        meta_description=meta_description,
        canonical_url=canonical_url,
        fingerprint=fingerprint,
    )


def make_section(
    *,
    section_index: int = 0,
    dom_id: str | None = "hero",
    classes: list[str] | None = None,
    headings: list[dict[str, object]] | None = None,
    text: str = "SoraMinds is ...",
    child_count: int = 5,
    fingerprint: str = "b" * 64,
) -> SectionRow:
    return SectionRow(
        section_index=section_index,
        dom_id=dom_id,
        classes=classes if classes is not None else ["hero", "container"],
        headings=(
            headings
            if headings is not None
            else [{"level": 1, "text": "About SoraMinds"}]
        ),
        text=text,
        child_count=child_count,
        fingerprint=fingerprint,
    )


def test_persists_page_with_nullable_metadata(
    session_factory: sessionmaker[Session],
) -> None:
    page = make_page(title=None, meta_description=None, canonical_url=None)

    with session_factory() as session:
        session.add(page)
        session.commit()
        page_id = page.id

    with session_factory() as session:
        stored_page = session.get(PageRow, page_id)

    assert stored_page is not None
    assert stored_page.url == "https://soraminds.com/about/"
    assert stored_page.title is None
    assert stored_page.meta_description is None
    assert stored_page.canonical_url is None
    assert stored_page.fingerprint == "a" * 64


def test_persists_sections_through_page_relationship(
    session_factory: sessionmaker[Session],
) -> None:
    page = make_page()
    page.sections.append(make_section(dom_id=None))

    with session_factory() as session:
        session.add(page)
        session.commit()
        page_id = page.id

    with session_factory() as session:
        stored_page = session.get(PageRow, page_id)
        assert stored_page is not None
        stored_section = stored_page.sections[0]
        assert stored_section.page is stored_page
        assert stored_section.dom_id is None
        assert stored_section.classes == ["hero", "container"]
        assert stored_section.headings == [
            {"level": 1, "text": "About SoraMinds"}
        ]
        assert stored_section.text == "SoraMinds is ..."
        assert stored_section.child_count == 5
        assert stored_section.fingerprint == "b" * 64


def test_returns_sections_in_section_index_order(
    session_factory: sessionmaker[Session],
) -> None:
    page = make_page()
    page.sections.extend(
        [
            make_section(section_index=2, text="Third"),
            make_section(section_index=0, text="First"),
            make_section(section_index=1, text="Second"),
        ]
    )

    with session_factory() as session:
        session.add(page)
        session.commit()
        page_id = page.id

    with session_factory() as session:
        stored_page = session.get(PageRow, page_id)
        assert stored_page is not None
        assert [section.section_index for section in stored_page.sections] == [
            0,
            1,
            2,
        ]


def test_page_url_must_be_unique(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        session.add_all([make_page(), make_page()])
        with pytest.raises(IntegrityError):
            session.commit()


def test_page_section_index_must_be_unique(
    session_factory: sessionmaker[Session],
) -> None:
    page = make_page()
    page.sections.extend([make_section(), make_section()])

    with session_factory() as session:
        session.add(page)
        with pytest.raises(IntegrityError):
            session.commit()


def test_deleting_page_cascades_to_sections(
    session_factory: sessionmaker[Session],
) -> None:
    page = make_page()
    page.sections.append(make_section())

    with session_factory() as session:
        session.add(page)
        session.commit()
        page_id = page.id
        section_id = page.sections[0].id
        session.execute(delete(PageRow).where(PageRow.id == page_id))
        session.commit()

    with session_factory() as session:
        assert session.get(SectionRow, section_id) is None


def test_json_and_numeric_defaults_are_independent(
    session_factory: sessionmaker[Session],
) -> None:
    page = make_page()
    page.sections.extend(
        [
            SectionRow(section_index=0, text="First", fingerprint="b" * 64),
            SectionRow(section_index=1, text="Second", fingerprint="c" * 64),
        ]
    )

    with session_factory() as session:
        session.add(page)
        session.commit()
        assert page.sections[0].classes == []
        assert page.sections[0].headings == []
        assert page.sections[0].child_count == 0
        assert page.sections[0].classes is not page.sections[1].classes
        assert page.sections[0].headings is not page.sections[1].headings


def test_schema_creates_required_indexes(engine: Engine) -> None:
    page_indexes = {
        tuple(index["column_names"])
        for index in inspect(engine).get_indexes("pages")
    }
    section_indexes = {
        tuple(index["column_names"])
        for index in inspect(engine).get_indexes("sections")
    }

    assert ("fingerprint",) in page_indexes
    assert ("page_id",) in section_indexes
    assert ("fingerprint",) in section_indexes
