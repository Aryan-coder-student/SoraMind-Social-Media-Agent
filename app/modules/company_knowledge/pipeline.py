"""Run the Phase 1 Company Knowledge pipeline."""

from app.modules.company_knowledge.crawl.base import CrawlStrategy
from app.modules.company_knowledge.models.crawl import (
    CrawlIncompleteReason,
    CrawlResult,
)
from app.modules.company_knowledge.services.base import PageBuildResult, ProcessedPage
from app.modules.company_knowledge.services.change_service import (
    CompanyKnowledgeChangeService,
)
from app.modules.company_knowledge.services.discovery_service import (
    CompanyKnowledgeDiscoveryService,
)
from app.repository.base import Repository


class IncompleteCrawlError(RuntimeError):
    """Raised when missing-page deactivation is requested for a partial crawl."""

    def __init__(self, reasons: set[CrawlIncompleteReason]) -> None:
        self.reasons = frozenset(reasons)
        reason_names = ", ".join(sorted(reason.value for reason in reasons))
        super().__init__(
            f"cannot deactivate missing pages after an incomplete crawl: "
            f"{reason_names}"
        )


class CompanyKnowledgePipeline:
    """Coordinate discovery, change analysis, and crawl missing-page deactivation."""

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
    ) -> list[PageBuildResult]:
        """Process discovered pages without reconciling missing URLs."""
        crawl_result = await self.crawler.discover(seed_url)
        processed_pages = await self._process_discovered_pages(crawl_result)
        return self._build_page_results(processed_pages)

    async def run_and_deactivate_missing_pages(
        self,
        seed_url: str,
    ) -> list[PageBuildResult]:
        """Run a complete crawl and deactivate pages it no longer finds."""
        crawl_result = await self.crawler.discover(seed_url)
        self._require_complete_crawl(crawl_result)

        processed_pages = await self._process_discovered_pages(crawl_result)
        page_results = self._build_page_results(processed_pages)
        processed_urls = {
            processed_page.page.url
            for processed_page in processed_pages
        }
        self.repository.mark_missing_pages_inactive(processed_urls)
        return page_results

    async def _process_discovered_pages(
        self,
        crawl_result: CrawlResult,
    ) -> list[ProcessedPage]:
        """Extract, normalize, fingerprint, and persist discovered pages."""
        processed_pages: list[ProcessedPage] = []
        for discovered_url in crawl_result.urls:
            processed_page = await self.discovery_service.process(
                str(discovered_url.url)
            )
            processed_pages.append(processed_page)

        return processed_pages

    def _build_page_results(
        self,
        processed_pages: list[ProcessedPage],
    ) -> list[PageBuildResult]:
        """Analyze persisted pages and return public pipeline results."""
        return [
            PageBuildResult(
                url=processed_page.page.url,
                save_result=processed_page.save_result,
                section_changes=self.change_service.get_changes(processed_page),
            )
            for processed_page in processed_pages
        ]

    @staticmethod
    def _require_complete_crawl(crawl_result: CrawlResult) -> None:
        """Reject missing-page deactivation unless BFS proved the crawl was complete."""
        if not crawl_result.is_complete:
            raise IncompleteCrawlError(crawl_result.incomplete_reasons)
