"""Tests for deterministic page change service."""

from datetime import UTC, datetime
from unittest.mock import Mock

from app.modules.company_knowledge.models.page import (
    Heading,
    PageDocument,
    PageSection,
)
from app.modules.company_knowledge.models.version import (
    PageVersion,
    SavePageResult,
    SavePageStatus,
    SectionVersion,
)
from app.modules.company_knowledge.services.base import ProcessedPage
from app.modules.company_knowledge.services.change_service import (
    CompanyKnowledgeChangeService,
)
from app.repository.base import Repository


def make_processed_page(status: SavePageStatus) -> ProcessedPage:
    page = PageDocument(
        url="https://example.com/pricing",
        title="Pricing",
        sections=[
            PageSection(
                index=0,
                headings=[Heading(level=2, text="Pricing")],
                text="New pricing",
            )
        ],
    )
    return ProcessedPage(
        page=page,
        save_result=SavePageResult(
            status=status,
            version_number=2 if status == SavePageStatus.CHANGED else 1,
        ),
        section_fingerprints=("b" * 64,),
    )


def test_non_changed_page_skips_version_lookup() -> None:
    repository = Mock(spec=Repository)
    service = CompanyKnowledgeChangeService(repository=repository)

    changes = service.get_changes(
        make_processed_page(SavePageStatus.UNCHANGED)
    )

    assert changes is None
    repository.get_page_version.assert_not_called()


def test_changed_page_compares_previous_and_current_sections() -> None:
    repository = Mock(spec=Repository)
    processed_page = make_processed_page(SavePageStatus.CHANGED)

    repository.get_page_version.return_value = PageVersion(
        version_number=1,
        url=processed_page.page.url,
        title="Pricing",
        fingerprint="a" * 64,
        captured_at=datetime.now(UTC),
        sections=[
            SectionVersion(
                index=0,
                headings=[Heading(level=2, text="Pricing")],
                text="Old pricing",
                fingerprint="a" * 64,
            )
        ],
    )

    service = CompanyKnowledgeChangeService(repository=repository)

    changes = service.get_changes(processed_page)

    repository.get_page_version.assert_called_once_with(
        processed_page.page.url,
        1,
    )
    assert changes is not None
    assert len(changes.changed) == 1
    assert changes.changed[0].before.text == "Old pricing"
    assert changes.changed[0].after.text == "New pricing"
