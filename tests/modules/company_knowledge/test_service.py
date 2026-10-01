"""Tests for Company Knowledge service orchestration."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest

from app.modules.company_knowledge.crawl.base import CrawlStrategy
from app.modules.company_knowledge.discovery.base import PageDiscoveryBase
from app.modules.company_knowledge.fingerprint.sha256 import (
    fingerprint_page,
    fingerprint_section,
)
from app.modules.company_knowledge.models.crawl import CrawlResult, DiscoveredURL
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
from app.modules.company_knowledge.normalization.base import NormalizerBase
from app.modules.company_knowledge.service import CompanyKnowledgeService
from app.repository.base import Repository


def make_page(text: str = "Current pricing") -> PageDocument:
    """Build one normalized page for service tests."""
    return PageDocument(
        url="https://example.com/pricing",
        title="Pricing",
        sections=[
            PageSection(
                index=0,
                headings=[Heading(level=2, text="Pricing")],
                text=text,
            )
        ],
    )


def make_service(
    *,
    page: PageDocument | None = None,
    save_result: SavePageResult | None = None,
) -> tuple[
    CompanyKnowledgeService,
    Mock,
    Mock,
    Mock,
    Mock,
]:
    """Build service dependencies with one discovered page."""
    page = page or make_page()
    save_result = save_result or SavePageResult(
        status=SavePageStatus.NEW,
        version_number=1,
    )

    crawler = Mock(spec=CrawlStrategy)
    crawler.discover = AsyncMock(
        return_value=CrawlResult(
            seed_url="https://example.com",
            urls=[
                DiscoveredURL(
                    url=page.url,
                    depth=0,
                )
            ],
        )
    )

    discovery = Mock(spec=PageDiscoveryBase)
    discovery.extract = AsyncMock(return_value=page)

    normalizer = Mock(spec=NormalizerBase)
    normalizer.normalize.return_value = page

    repository = Mock(spec=Repository)
    repository.save_page.return_value = save_result
    repository.mark_missing_pages_inactive.return_value = []

    service = CompanyKnowledgeService(
        crawler=crawler,
        discovery=discovery,
        normalizer=normalizer,
        repository=repository,
    )

    return service, crawler, discovery, normalizer, repository


@pytest.mark.asyncio
async def test_build_runs_pipeline_and_persists_page() -> None:
    page = make_page()
    service, crawler, discovery, normalizer, repository = make_service(page=page)

    results = await service.build("https://example.com")

    crawler.discover.assert_awaited_once_with("https://example.com")
    discovery.extract.assert_awaited_once_with(str(page.url))
    normalizer.normalize.assert_called_once_with(page)

    expected_section_fingerprints = [
        fingerprint_section(section)
        for section in page.sections
    ]
    repository.save_page.assert_called_once_with(
        page,
        fingerprint_page(page),
        expected_section_fingerprints,
    )

    assert len(results) == 1
    assert results[0].url == page.url
    assert results[0].save_result.status == SavePageStatus.NEW
    assert results[0].section_changes is None


@pytest.mark.asyncio
async def test_changed_page_returns_section_changes() -> None:
    current_page = make_page("New pricing")
    service, _, _, _, repository = make_service(
        page=current_page,
        save_result=SavePageResult(
            status=SavePageStatus.CHANGED,
            version_number=2,
        ),
    )
    repository.get_page_version.return_value = PageVersion(
        version_number=1,
        url=current_page.url,
        title="Pricing",
        fingerprint="a" * 64,
        captured_at=datetime.now(UTC),
        sections=[
            SectionVersion(
                index=0,
                headings=[Heading(level=2, text="Pricing")],
                text="Old pricing",
                fingerprint="b" * 64,
            )
        ],
    )

    results = await service.build("https://example.com")

    repository.get_page_version.assert_called_once_with(current_page.url, 1)

    changes = results[0].section_changes
    assert changes is not None
    assert changes.added == ()
    assert changes.removed == ()
    assert len(changes.changed) == 1
    assert changes.changed[0].before.text == "Old pricing"
    assert changes.changed[0].after.text == "New pricing"


@pytest.mark.asyncio
async def test_authoritative_build_reconciles_missing_pages() -> None:
    page = make_page()
    service, _, _, _, repository = make_service(page=page)

    await service.build(
        "https://example.com",
        authoritative=True,
    )

    repository.mark_missing_pages_inactive.assert_called_once_with({page.url})


@pytest.mark.asyncio
async def test_non_authoritative_build_does_not_reconcile_missing_pages() -> None:
    service, _, _, _, repository = make_service()

    await service.build("https://example.com")

    repository.mark_missing_pages_inactive.assert_not_called()


@pytest.mark.asyncio
async def test_failed_page_processing_does_not_reconcile_missing_pages() -> None:
    service, _, discovery, _, repository = make_service()
    discovery.extract.side_effect = RuntimeError("page extraction failed")

    with pytest.raises(RuntimeError, match="page extraction failed"):
        await service.build(
            "https://example.com",
            authoritative=True,
        )

    repository.mark_missing_pages_inactive.assert_not_called()
