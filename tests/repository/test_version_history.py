"""Behavior tests for immutable page history and page lifecycle state."""

from datetime import UTC

import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.database.connections.sqlite import SQLiteConnection
from app.database.schemas.page import PageRow
from app.database.schemas.version import PageVersionRow
from app.modules.company_knowledge.models.page import Heading, PageDocument, PageSection
from app.modules.company_knowledge.models.version import SavePageStatus
from app.repository.operations import sqlalchemy as repository_module
from app.repository.operations.sqlalchemy import SQLAlchemyRepository


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


@pytest.fixture
def repository(
    session_factory: sessionmaker[Session],
) -> SQLAlchemyRepository:
    return SQLAlchemyRepository(session_factory)


def make_section(index: int, text: str, dom_id: str | None = None) -> PageSection:
    return PageSection(
        index=index,
        id=dom_id,
        classes=[f"section-{index}"],
        headings=[Heading(level=2, text=f"Heading {index}")],
        text=text,
        child_count=index + 1,
    )


def make_page(
    *,
    url: str = "https://soraminds.com/about/",
    title: str = "About SoraMinds",
    canonical_url: str | None = "https://soraminds.com/about/",
    sections: list[PageSection] | None = None,
) -> PageDocument:
    return PageDocument(
        url=url,
        title=title,
        meta_description="Learn about SoraMinds",
        canonical_url=canonical_url,
        sections=sections or [make_section(0, "Original", "hero")],
    )


def save(
    repository: SQLAlchemyRepository,
    page: PageDocument,
    page_fingerprint: str,
    section_fingerprints: list[str],
):
    return repository.save_page(
        page,
        page_fingerprint=page_fingerprint,
        section_fingerprints=section_fingerprints,
    )


def test_first_saved_page_creates_version_one(repository: SQLAlchemyRepository) -> None:
    page = make_page()

    result = save(repository, page, "a" * 64, ["b" * 64])

    assert result.status is SavePageStatus.NEW
    assert result.version_number == 1


def test_new_page_points_to_version_one(
    repository: SQLAlchemyRepository,
    session_factory: sessionmaker[Session],
) -> None:
    page = make_page()
    save(repository, page, "a" * 64, ["b" * 64])

    with session_factory() as session:
        stored_page = session.scalar(select(PageRow))
        assert stored_page is not None
        current_version = session.get(
            PageVersionRow,
            stored_page.current_version_id,
        )

    assert current_version is not None
    assert current_version.version_number == 1
    assert current_version.fingerprint == "a" * 64


def test_version_one_contains_all_section_snapshots(
    repository: SQLAlchemyRepository,
) -> None:
    page = make_page(
        sections=[make_section(0, "First", "first"), make_section(1, "Second")]
    )
    save(repository, page, "a" * 64, ["b" * 64, "c" * 64])

    version = repository.get_page_version(page.url, 1)

    assert [section.index for section in version.sections] == [0, 1]
    assert [section.fingerprint for section in version.sections] == ["b" * 64, "c" * 64]
    assert [section.text for section in version.sections] == ["First", "Second"]
    assert [section.headings[0].text for section in version.sections] == [
        "Heading 0",
        "Heading 1",
    ]


def test_identical_fingerprint_creates_no_version_two(
    repository: SQLAlchemyRepository,
) -> None:
    page = make_page()
    save(repository, page, "a" * 64, ["b" * 64])

    result = save(repository, page, "a" * 64, ["b" * 64])

    assert result.status is SavePageStatus.UNCHANGED
    assert result.version_number == 1
    assert len(repository.get_page_versions(page.url)) == 1


def test_changed_fingerprint_creates_version_two(
    repository: SQLAlchemyRepository,
    session_factory: sessionmaker[Session],
) -> None:
    page = make_page()
    save(repository, page, "a" * 64, ["b" * 64])

    with session_factory() as session:
        first_version_id = session.scalar(select(PageRow.current_version_id))

    result = save(repository, make_page(title="Updated"), "c" * 64, ["d" * 64])

    with session_factory() as session:
        second_version_id = session.scalar(select(PageRow.current_version_id))
        current_version = session.get(PageVersionRow, second_version_id)

    assert result.status is SavePageStatus.CHANGED
    assert result.version_number == 2
    assert second_version_id != first_version_id
    assert current_version is not None
    assert current_version.version_number == 2


def test_version_numbers_increment_per_page(repository: SQLAlchemyRepository) -> None:
    page = make_page()
    save(repository, page, "a" * 64, ["1" * 64])
    save(repository, make_page(title="Second"), "b" * 64, ["2" * 64])
    save(repository, make_page(title="Third"), "c" * 64, ["3" * 64])

    assert [
        item.version_number
        for item in repository.get_page_versions(page.url)
    ] == [1, 2, 3]


def test_different_pages_have_independent_version_numbers(
    repository: SQLAlchemyRepository,
) -> None:
    about = make_page()
    contact = make_page(url="https://soraminds.com/contact/")

    assert save(repository, about, "a" * 64, ["b" * 64]).version_number == 1
    assert save(repository, contact, "c" * 64, ["d" * 64]).version_number == 1


def test_old_version_remains_unchanged(repository: SQLAlchemyRepository) -> None:
    page = make_page(title="Original")
    save(repository, page, "a" * 64, ["b" * 64])
    save(repository, make_page(title="Changed"), "c" * 64, ["d" * 64])

    old_version = repository.get_page_version(page.url, 1)

    assert old_version.title == "Original"
    assert old_version.sections[0].text == "Original"


def test_added_section_appears_only_in_new_version(
    repository: SQLAlchemyRepository,
) -> None:
    page = make_page()
    save(repository, page, "a" * 64, ["1" * 64])
    save(
        repository,
        make_page(sections=[make_section(0, "Original"), make_section(1, "Added")]),
        "b" * 64,
        ["1" * 64, "2" * 64],
    )

    assert len(repository.get_page_version(page.url, 1).sections) == 1
    assert len(repository.get_page_version(page.url, 2).sections) == 2


def test_removed_section_remains_only_in_old_version(
    repository: SQLAlchemyRepository,
) -> None:
    page = make_page(sections=[make_section(0, "First"), make_section(1, "Removed")])
    save(repository, page, "a" * 64, ["1" * 64, "2" * 64])
    save(
        repository,
        make_page(sections=[make_section(0, "First")]),
        "b" * 64,
        ["1" * 64],
    )

    assert [
        item.text
        for item in repository.get_page_version(page.url, 1).sections
    ] == ["First", "Removed"]
    assert [
        item.text
        for item in repository.get_page_version(page.url, 2).sections
    ] == ["First"]


def test_changed_section_fingerprint_is_in_new_version(
    repository: SQLAlchemyRepository,
) -> None:
    page = make_page()
    save(repository, page, "a" * 64, ["1" * 64])
    save(repository, make_page(), "b" * 64, ["2" * 64])

    assert repository.get_page_version(page.url, 1).sections[0].fingerprint == "1" * 64
    assert repository.get_page_version(page.url, 2).sections[0].fingerprint == "2" * 64


def test_get_page_versions_returns_version_number_order(
    repository: SQLAlchemyRepository,
) -> None:
    page = make_page()
    save(repository, page, "a" * 64, ["1" * 64])
    save(repository, make_page(title="Second"), "b" * 64, ["2" * 64])

    assert [
        item.version_number
        for item in repository.get_page_versions(page.url)
    ] == [1, 2]


def test_get_page_version_returns_exact_snapshot(
    repository: SQLAlchemyRepository,
) -> None:
    page = make_page(title="First")
    save(repository, page, "a" * 64, ["b" * 64])
    save(repository, make_page(title="Second"), "c" * 64, ["d" * 64])

    version = repository.get_page_version(page.url, 1)

    assert version.title == "First"
    assert version.url == page.url
    assert version.captured_at.tzinfo is not None
    assert version.captured_at.astimezone(UTC).utcoffset().total_seconds() == 0


def test_get_latest_version_returns_latest_snapshot(
    repository: SQLAlchemyRepository,
) -> None:
    page = make_page()
    save(repository, page, "a" * 64, ["b" * 64])
    save(repository, make_page(title="Latest"), "c" * 64, ["d" * 64])

    latest = repository.get_latest_version(page.url)

    assert latest.version_number == 2
    assert latest.title == "Latest"


@pytest.mark.parametrize(
    ("method_name", "arguments"),
    [
        ("get_page_versions", ("not-a-url",)),
        ("get_page_version", ("not-a-url", 1)),
        ("get_latest_version", ("not-a-url",)),
        ("mark_missing_pages_inactive", ({"not-a-url"},)),
    ],
)
def test_version_methods_reject_invalid_urls(
    repository: SQLAlchemyRepository,
    method_name: str,
    arguments: tuple[object, ...],
) -> None:
    with pytest.raises(ValidationError):
        getattr(repository, method_name)(*arguments)


def test_changed_version_and_current_update_are_atomic(
    repository: SQLAlchemyRepository,
) -> None:
    page = make_page()
    save(repository, page, "a" * 64, ["b" * 64])
    save(repository, make_page(title="Changed"), "c" * 64, ["d" * 64])

    assert repository.get_page(page.url).title == "Changed"
    assert repository.get_latest_version(page.url).title == "Changed"


def test_snapshot_failure_rolls_back_history_and_current_state(
    repository: SQLAlchemyRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = make_page(title="Original")
    save(repository, page, "a" * 64, ["b" * 64])

    def fail_snapshot(*args: object, **kwargs: object) -> None:
        raise RuntimeError("snapshot failed")

    monkeypatch.setattr(repository_module, "section_to_version_row", fail_snapshot)

    with pytest.raises(RuntimeError, match="snapshot failed"):
        save(repository, make_page(title="Changed"), "c" * 64, ["d" * 64])

    assert repository.get_page(page.url).title == "Original"
    assert repository.get_page_fingerprint(page.url) == "a" * 64
    assert len(repository.get_page_versions(page.url)) == 1


def test_missing_active_page_is_marked_inactive(
    repository: SQLAlchemyRepository,
    session_factory: sessionmaker[Session],
) -> None:
    page = make_page()
    save(repository, page, "a" * 64, ["b" * 64])

    marked_urls = repository.mark_missing_pages_inactive(set())

    assert [str(url) for url in marked_urls] == [str(page.url)]
    with session_factory() as session:
        assert session.scalar(select(PageRow.is_active)) is False


def test_seen_page_remains_active(
    repository: SQLAlchemyRepository,
    session_factory: sessionmaker[Session],
) -> None:
    page = make_page()
    save(repository, page, "a" * 64, ["b" * 64])

    assert repository.mark_missing_pages_inactive({page.url}) == []
    with session_factory() as session:
        assert session.scalar(select(PageRow.is_active)) is True


def test_already_inactive_page_is_not_marked_again(
    repository: SQLAlchemyRepository,
) -> None:
    page = make_page()
    save(repository, page, "a" * 64, ["b" * 64])
    repository.mark_missing_pages_inactive(set())

    assert repository.mark_missing_pages_inactive(set()) == []


def test_reappearing_page_becomes_active_again(
    repository: SQLAlchemyRepository,
    session_factory: sessionmaker[Session],
) -> None:
    page = make_page()
    save(repository, page, "a" * 64, ["b" * 64])
    repository.mark_missing_pages_inactive(set())

    result = save(repository, page, "a" * 64, ["b" * 64])

    assert result.status is SavePageStatus.REACTIVATED
    assert result.version_number == 1
    with session_factory() as session:
        assert session.scalar(select(PageRow.is_active)) is True


def test_deactivation_keeps_historical_versions(
    repository: SQLAlchemyRepository,
) -> None:
    page = make_page()
    save(repository, page, "a" * 64, ["b" * 64])

    repository.mark_missing_pages_inactive(set())

    assert len(repository.get_page_versions(page.url)) == 1


def test_unchanged_fingerprint_keeps_current_version_immutable(
    repository: SQLAlchemyRepository,
    session_factory: sessionmaker[Session],
) -> None:
    page = make_page()
    refreshed = make_page(
        canonical_url="https://www.soraminds.com/about/",
        sections=[make_section(0, "Original", "new-dom-id")],
    )
    save(repository, page, "a" * 64, ["b" * 64])

    with session_factory() as session:
        original_version_id = session.scalar(select(PageRow.current_version_id))

    result = save(repository, refreshed, "a" * 64, ["b" * 64])

    with session_factory() as session:
        current_version_id = session.scalar(select(PageRow.current_version_id))

    stored_page = repository.get_page(page.url)

    assert result.status is SavePageStatus.UNCHANGED
    assert len(repository.get_page_versions(page.url)) == 1
    assert current_version_id == original_version_id
    assert stored_page is not None
    assert stored_page.canonical_url is None
    assert stored_page.sections[0].id is None
    assert stored_page.sections[0].classes == []
    assert stored_page.sections[0].child_count == 0


def test_current_page_read_rejects_foreign_version_pointer(
    repository: SQLAlchemyRepository,
    session_factory: sessionmaker[Session],
) -> None:
    first = make_page(url="https://soraminds.com/first/")
    second = make_page(url="https://soraminds.com/second/")

    save(repository, first, "a" * 64, ["b" * 64])
    save(repository, second, "c" * 64, ["d" * 64])

    with session_factory() as session:
        first_row = session.scalar(
            select(PageRow).where(PageRow.url == str(first.url))
        )
        second_row = session.scalar(
            select(PageRow).where(PageRow.url == str(second.url))
        )
        assert first_row is not None
        assert second_row is not None
        first_row.current_version_id = second_row.current_version_id
        session.commit()

    assert repository.get_page(first.url) is None
    assert repository.get_page_fingerprint(first.url) is None


def test_save_rejects_foreign_current_version_pointer(
    repository: SQLAlchemyRepository,
    session_factory: sessionmaker[Session],
) -> None:
    first = make_page(url="https://soraminds.com/first/")
    second = make_page(url="https://soraminds.com/second/")

    save(repository, first, "a" * 64, ["b" * 64])
    save(repository, second, "c" * 64, ["d" * 64])

    with session_factory() as session:
        first_row = session.scalar(
            select(PageRow).where(PageRow.url == str(first.url))
        )
        second_row = session.scalar(
            select(PageRow).where(PageRow.url == str(second.url))
        )
        assert first_row is not None
        assert second_row is not None
        first_row.current_version_id = second_row.current_version_id
        session.commit()

    with pytest.raises(RuntimeError, match="does not belong"):
        save(repository, first, "e" * 64, ["f" * 64])
