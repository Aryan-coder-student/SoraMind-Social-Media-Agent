"""Tests for Company Knowledge pipeline orchestration."""

from unittest.mock import AsyncMock, Mock

import pytest

from app.modules.company_knowledge.crawl.base import CrawlStrategy
from app.modules.company_knowledge.models.crawl import CrawlResult, DiscoveredURL
from app.modules.company_knowledge.models.page import PageDocument
from app.modules.company_knowledge.models.section_change import SectionChangeSet
from app.modules.company_knowledge.models.version import (
    SavePageResult,
    SavePageStatus,
)
from app.modules.company_knowledge.pipeline import CompanyKnowledgePipeline
from app.modules.company_knowledge.services.base import ProcessedPage
from app.modules.company_knowledge.services.change_service import (
    CompanyKnowledgeChangeService,
)
from app.modules.company_knowledge.services.discovery_service import (
    CompanyKnowledgeDiscoveryService,
)
from app.repository.base import Repository


def make_processed_page() -> ProcessedPage:
    page = PageDocument(
        url="https://example.com/pricing",
        title="Pricing",
        sections=[],
    )
    return ProcessedPage(
        page=page,
        save_result=SavePageResult(
            status=SavePageStatus.NEW,
            version_number=1,
        ),
        section_fingerprints=(),
    )


def make_pipeline() -> tuple[
    CompanyKnowledgePipeline,
    Mock,
    Mock,
    Mock,
    Mock,
]:
    processed_page = make_processed_page()

    crawler = Mock(spec=CrawlStrategy)
    crawler.discover = AsyncMock(
        return_value=CrawlResult(
            seed_url="https://example.com",
            urls=[
                DiscoveredURL(
                    url=processed_page.page.url,
                    depth=0,
                )
            ],
        )
    )

    discovery_service = Mock(spec=CompanyKnowledgeDiscoveryService)
    discovery_service.process = AsyncMock(return_value=processed_page)

    change_service = Mock(spec=CompanyKnowledgeChangeService)
    change_service.get_changes.return_value = SectionChangeSet()

    repository = Mock(spec=Repository)
    repository.mark_missing_pages_inactive.return_value = []

    pipeline = CompanyKnowledgePipeline(
        crawler=crawler,
        discovery_service=discovery_service,
        change_service=change_service,
        repository=repository,
    )

    return (
        pipeline,
        crawler,
        discovery_service,
        change_service,
        repository,
    )


@pytest.mark.asyncio
async def test_run_coordinates_discovery_and_change_services() -> None:
    (
        pipeline,
        crawler,
        discovery_service,
        change_service,
        _,
    ) = make_pipeline()

    results = await pipeline.run("https://example.com")

    crawler.discover.assert_awaited_once_with("https://example.com")
    discovery_service.process.assert_awaited_once_with(
        "https://example.com/pricing"
    )

    processed_page = discovery_service.process.return_value
    change_service.get_changes.assert_called_once_with(processed_page)

    assert len(results) == 1
    assert results[0].url == processed_page.page.url
    assert results[0].save_result == processed_page.save_result
    assert results[0].section_changes == SectionChangeSet()


@pytest.mark.asyncio
async def test_authoritative_run_reconciles_processed_page_urls() -> None:
    pipeline, _, discovery_service, _, repository = make_pipeline()

    await pipeline.run(
        "https://example.com",
        authoritative_crawl=True,
    )

    processed_page = discovery_service.process.return_value
    repository.mark_missing_pages_inactive.assert_called_once_with(
        {processed_page.page.url}
    )


@pytest.mark.asyncio
async def test_non_authoritative_run_skips_reconciliation() -> None:
    pipeline, _, _, _, repository = make_pipeline()

    await pipeline.run("https://example.com")

    repository.mark_missing_pages_inactive.assert_not_called()


@pytest.mark.asyncio
async def test_processing_failure_skips_reconciliation() -> None:
    pipeline, _, discovery_service, _, repository = make_pipeline()
    discovery_service.process.side_effect = RuntimeError("processing failed")

    with pytest.raises(RuntimeError, match="processing failed"):
        await pipeline.run(
            "https://example.com",
            authoritative_crawl=True,
        )

    repository.mark_missing_pages_inactive.assert_not_called()
