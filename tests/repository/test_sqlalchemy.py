"""Tests for current-state Company Knowledge persistence."""

import pytest
from pydantic import HttpUrl, ValidationError
from sqlalchemy.orm import Session, sessionmaker

from app.database.connections.sqlite import SQLiteConnection
from app.modules.company_knowledge.models.page import Heading, PageDocument, PageSection
from app.repository.base import Repository
from app.repository.operations.sqlalchemy import SQLAlchemyRepository


@pytest.fixture
def database() -> SQLiteConnection:
    connection = SQLiteConnection("sqlite:///:memory:")
    connection.connect()
    connection.create_tables()
    yield connection
    connection.close()


@pytest.fixture
def session_factory(
    database: SQLiteConnection,
) -> sessionmaker[Session]:
    return database.create_session_factory()


@pytest.fixture
def repository(
    session_factory: sessionmaker[Session],
) -> SQLAlchemyRepository:
    return SQLAlchemyRepository(session_factory)


def make_page(
    *,
    url: str = "https://soraminds.com/about/",
    title: str | None = "About SoraMinds",
    meta_description: str | None = "Learn about SoraMinds",
    canonical_url: str | None = "https://soraminds.com/about/",
    sections: list[PageSection] | None = None,
) -> PageDocument:
    return PageDocument(
        url=url,
        title=title,
        meta_description=meta_description,
        canonical_url=canonical_url,
        sections=sections if sections is not None else [
            PageSection(
                index=0,
                id="hero",
                classes=["hero", "container"],
                headings=[Heading(level=1, text="About SoraMinds")],
                text="SoraMinds is ...",
                child_count=5,
            )
        ],
    )


def test_sqlalchemy_repository_implements_repository_contract(
    repository: SQLAlchemyRepository,
) -> None:
    assert isinstance(repository, Repository)


def test_save_and_get_page(
    repository: SQLAlchemyRepository,
) -> None:
    page = make_page()

    repository.save_page(
        page,
        page_fingerprint="a" * 64,
        section_fingerprints=["b" * 64],
    )

    stored_page = repository.get_page(page.url)

    assert stored_page is not None
    assert stored_page.url == page.url
    assert stored_page.title == page.title
    assert stored_page.meta_description == page.meta_description
    assert stored_page.canonical_url is None
    assert stored_page.sections[0].headings == page.sections[0].headings
    assert stored_page.sections[0].text == page.sections[0].text
    assert stored_page.sections[0].id is None
    assert stored_page.sections[0].classes == []
    assert stored_page.sections[0].child_count == 0


def test_get_page_returns_none_for_unknown_url(
    repository: SQLAlchemyRepository,
) -> None:
    assert repository.get_page(HttpUrl("https://soraminds.com/missing/")) is None


def test_get_page_fingerprint(
    repository: SQLAlchemyRepository,
) -> None:
    page = make_page()

    repository.save_page(
        page,
        page_fingerprint="a" * 64,
        section_fingerprints=["b" * 64],
    )

    assert repository.get_page_fingerprint(page.url) == "a" * 64


def test_get_page_fingerprint_returns_none_for_unknown_url(
    repository: SQLAlchemyRepository,
) -> None:
    assert (
        repository.get_page_fingerprint(
            HttpUrl("https://soraminds.com/missing/")
        )
        is None
    )


def test_save_page_updates_existing_current_state(
    repository: SQLAlchemyRepository,
) -> None:
    original = make_page()
    changed = make_page(
        title="Updated SoraMinds",
        meta_description="Updated description",
        sections=[
            PageSection(
                index=0,
                id="updated-hero",
                classes=["updated"],
                headings=[Heading(level=2, text="Updated")],
                text="Updated content",
                child_count=2,
            ),
            PageSection(
                index=1,
                id="details",
                classes=[],
                headings=[],
                text="New second section",
                child_count=1,
            ),
        ],
    )

    repository.save_page(
        original,
        page_fingerprint="a" * 64,
        section_fingerprints=["b" * 64],
    )
    repository.save_page(
        changed,
        page_fingerprint="c" * 64,
        section_fingerprints=["d" * 64, "e" * 64],
    )

    stored_page = repository.get_page(changed.url)

    assert stored_page is not None
    assert stored_page.title == changed.title
    assert stored_page.meta_description == changed.meta_description
    assert [section.text for section in stored_page.sections] == [
        section.text for section in changed.sections
    ]
    assert [section.headings for section in stored_page.sections] == [
        section.headings for section in changed.sections
    ]
    assert all(section.id is None for section in stored_page.sections)
    assert all(section.classes == [] for section in stored_page.sections)
    assert all(section.child_count == 0 for section in stored_page.sections)
    assert repository.get_page_fingerprint(changed.url) == "c" * 64


def test_save_page_replaces_removed_sections(
    repository: SQLAlchemyRepository,
) -> None:
    original = make_page(
        sections=[
            PageSection(index=0, text="First"),
            PageSection(index=1, text="Second"),
        ]
    )
    changed = make_page(
        sections=[
            PageSection(index=0, text="Only section"),
        ]
    )

    repository.save_page(
        original,
        page_fingerprint="a" * 64,
        section_fingerprints=["b" * 64, "c" * 64],
    )
    repository.save_page(
        changed,
        page_fingerprint="d" * 64,
        section_fingerprints=["e" * 64],
    )

    stored_page = repository.get_page(str(changed.url))

    assert stored_page is not None
    assert len(stored_page.sections) == 1
    assert stored_page.sections[0].text == "Only section"


def test_save_page_requires_one_fingerprint_per_section(
    repository: SQLAlchemyRepository,
) -> None:
    page = make_page(
        sections=[
            PageSection(index=0, text="First"),
            PageSection(index=1, text="Second"),
        ]
    )

    with pytest.raises(
        ValueError,
        match="section fingerprint count must match page section count",
    ):
        repository.save_page(
            page,
            page_fingerprint="a" * 64,
            section_fingerprints=["b" * 64],
        )


def test_delete_page_returns_true_and_removes_page(
    repository: SQLAlchemyRepository,
) -> None:
    page = make_page()

    repository.save_page(
        page,
        page_fingerprint="a" * 64,
        section_fingerprints=["b" * 64],
    )

    assert repository.delete_page(page.url) is True
    assert repository.get_page(page.url) is None


def test_delete_page_returns_false_for_unknown_url(
    repository: SQLAlchemyRepository,
) -> None:
    assert (
        repository.delete_page(HttpUrl("https://soraminds.com/missing/"))
        is False
    )


@pytest.mark.parametrize(
    "operation_name",
    [
        "get_page",
        "get_page_fingerprint",
        "delete_page",
    ],
)
def test_repository_rejects_invalid_lookup_urls(
    repository: SQLAlchemyRepository,
    operation_name: str,
) -> None:
    operation = getattr(repository, operation_name)

    with pytest.raises(ValidationError):
        operation("not-a-url")

