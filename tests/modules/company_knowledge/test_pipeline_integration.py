"""Integration tests for the Company Knowledge pipeline."""

from collections.abc import Sequence

import pytest
from sqlalchemy import select

from app.database.connections.sqlite import SQLiteConnection
from app.database.schemas.page import PageRow
from app.modules.company_knowledge.crawl.base import CrawlStrategy
from app.modules.company_knowledge.discovery.base import PageDiscoveryBase
from app.modules.company_knowledge.models.crawl import CrawlResult, DiscoveredURL
from app.modules.company_knowledge.models.page import (
    Heading,
    PageDocument,
    PageSection,
)
from app.modules.company_knowledge.models.version import SavePageStatus
from app.modules.company_knowledge.normalization.normalize import PageNormalizer
from app.modules.company_knowledge.normalization.text_cleaner import (
    UnicodeSanityAdapter,
)
from app.modules.company_knowledge.pipeline import CompanyKnowledgePipeline
from app.modules.company_knowledge.services.change_service import (
    CompanyKnowledgeChangeService,
)
from app.modules.company_knowledge.services.discovery_service import (
    CompanyKnowledgeDiscoveryService,
)
from app.repository.operations.sqlalchemy import SQLAlchemyRepository


class StaticCrawler(CrawlStrategy):
    """Return a mutable list of discovered URLs without network access."""

    def __init__(self, urls: Sequence[str]) -> None:
        self.urls = list(urls)

    async def discover(self, seed_url: str) -> CrawlResult:
        return CrawlResult(
            seed_url=seed_url,
            urls=[
                DiscoveredURL(
                    url=url,
                    depth=0,
                )
                for url in self.urls
            ],
        )


class MutablePageDiscovery(PageDiscoveryBase):
    """Return mutable factual page documents without launching a browser."""

    def __init__(self, pages: dict[str, PageDocument]) -> None:
        self.pages = pages

    async def extract(self, url: str) -> PageDocument:
        return self.pages[url]


def make_page(
    url: str,
    text: str,
    *,
    heading: str = "Pricing",
) -> PageDocument:
    return PageDocument(
        url=url,
        title=f"{heading}   Page",
        sections=[
            PageSection(
                index=0,
                headings=[Heading(level=2, text=heading)],
                text=text,
            )
        ],
    )


def make_pipeline(
    pages: dict[str, PageDocument],
    urls: Sequence[str],
) -> tuple[
    CompanyKnowledgePipeline,
    SQLAlchemyRepository,
    StaticCrawler,
    MutablePageDiscovery,
    SQLiteConnection,
]:
    database = SQLiteConnection("sqlite:///:memory:")
    database.create_tables()
    repository = SQLAlchemyRepository(database.create_session_factory())

    crawler = StaticCrawler(urls)
    discovery = MutablePageDiscovery(pages)

    discovery_service = CompanyKnowledgeDiscoveryService(
        discovery=discovery,
        normalizer=PageNormalizer(UnicodeSanityAdapter()),
        repository=repository,
    )
    change_service = CompanyKnowledgeChangeService(repository=repository)

    pipeline = CompanyKnowledgePipeline(
        crawler=crawler,
        discovery_service=discovery_service,
        change_service=change_service,
        repository=repository,
    )

    return pipeline, repository, crawler, discovery, database


@pytest.mark.asyncio
async def test_pipeline_persists_versions_and_classifies_changed_sections() -> None:
    url = "https://example.com/pricing"
    pages = {
        url: make_page(
            url,
            "Starter   plan",
        )
    }

    pipeline, repository, _, discovery, database = make_pipeline(
        pages,
        [url],
    )

    try:
        first_results = await pipeline.run("https://example.com")

        assert first_results[0].save_result.status == SavePageStatus.NEW
        assert first_results[0].section_changes is None

        first_version = repository.get_page_version(
            first_results[0].url,
            1,
        )
        assert first_version is not None
        assert first_version.title == "Pricing Page"
        assert first_version.sections[0].text == "Starter plan"

        discovery.pages[url] = make_page(
            url,
            "Starter and Pro plans",
        )

        second_results = await pipeline.run("https://example.com")

        assert second_results[0].save_result.status == SavePageStatus.CHANGED
        assert second_results[0].save_result.version_number == 2

        changes = second_results[0].section_changes
        assert changes is not None
        assert changes.added == ()
        assert changes.removed == ()
        assert len(changes.changed) == 1
        assert changes.changed[0].before.text == "Starter plan"
        assert changes.changed[0].after.text == "Starter and Pro plans"

        assert [
            version.version_number
            for version in repository.get_page_versions(second_results[0].url)
        ] == [1, 2]
    finally:
        database.close()


@pytest.mark.asyncio
async def test_complete_pipeline_run_deactivates_missing_pages() -> None:
    about_url = "https://example.com/about"
    pricing_url = "https://example.com/pricing"
    pages = {
        about_url: make_page(
            about_url,
            "About the company",
            heading="About",
        ),
        pricing_url: make_page(
            pricing_url,
            "Starter plan",
        ),
    }

    pipeline, _, crawler, _, database = make_pipeline(
        pages,
        [about_url, pricing_url],
    )

    try:
        await pipeline.run("https://example.com")

        crawler.urls = [about_url]
        await pipeline.run_and_deactivate_missing_pages(
            "https://example.com"
        )

        session_factory = database.create_session_factory()
        with session_factory() as session:
            page_states = dict(
                session.execute(
                    select(PageRow.url, PageRow.is_active)
                ).all()
            )

        assert page_states[about_url] is True
        assert page_states[pricing_url] is False
    finally:
        database.close()
