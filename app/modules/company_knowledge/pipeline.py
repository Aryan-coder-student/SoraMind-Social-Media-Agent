"""Run the Phase 1 Company Knowledge pipeline."""

from app.modules.company_knowledge.crawl.base import CrawlStrategy
from app.modules.company_knowledge.services.base import PageBuildResult, ProcessedPage
from app.modules.company_knowledge.services.change_service import (
    CompanyKnowledgeChangeService,
)
from app.modules.company_knowledge.services.discovery_service import (
    CompanyKnowledgeDiscoveryService,
)
from app.repository.base import Repository


class CompanyKnowledgePipeline:
    """Coordinate discovery, change analysis, and crawl reconciliation."""

    def __init__(
        self,
        crawler: CrawlStrategy,
        discovery_service: CompanyKnowledgeDiscoveryService,
        change_service: CompanyKnowledgeChangeService,
        repository: Repository,
    ) -> None:
        self.crawler = crawler
        self.discovery_service = discovery_service
        self.change_service = change_service
        self.repository = repository

    async def run(
        self,
        seed_url: str,
        *,
        authoritative_crawl: bool = False,
    ) -> list[PageBuildResult]:
        """Run one Company Knowledge crawl and processing cycle."""
        crawl_result = await self.crawler.discover(seed_url)

        processed_pages: list[ProcessedPage] = []
        for discovered_url in crawl_result.urls:
            processed_page = await self.discovery_service.process(
                str(discovered_url.url)
            )
            processed_pages.append(processed_page)

        page_results = [
            PageBuildResult(
                url=processed_page.page.url,
                save_result=processed_page.save_result,
                section_changes=self.change_service.get_changes(processed_page),
            )
            for processed_page in processed_pages
        ]

        if authoritative_crawl:
            processed_urls = {
                processed_page.page.url
                for processed_page in processed_pages
            }
            self.repository.mark_missing_pages_inactive(processed_urls)

        return page_results
