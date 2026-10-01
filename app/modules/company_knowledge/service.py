"""Orchestrate the Phase 1 Company Knowledge pipeline."""

from dataclasses import dataclass

from pydantic import HttpUrl

from app.modules.company_knowledge.crawl.base import CrawlStrategy
from app.modules.company_knowledge.discovery.base import PageDiscoveryBase
from app.modules.company_knowledge.fingerprint.sha256 import (
    fingerprint_page,
    fingerprint_section,
)
from app.modules.company_knowledge.models.page import PageDocument
from app.modules.company_knowledge.models.section_change import SectionChangeSet
from app.modules.company_knowledge.models.version import (
    SavePageResult,
    SavePageStatus,
    SectionVersion,
)
from app.modules.company_knowledge.normalization.base import NormalizerBase
from app.modules.company_knowledge.section_changes import classify_section_changes
from app.repository.base import Repository


@dataclass(frozen=True)
class PageBuildResult:
    """Persistence and section-change result for one processed page."""

    url: HttpUrl
    save_result: SavePageResult
    section_changes: SectionChangeSet | None = None


class CompanyKnowledgeService:
    """Coordinate crawl, extraction, normalization, versioning, and diffing."""

    def __init__(
        self,
        crawler: CrawlStrategy,
        discovery: PageDiscoveryBase,
        normalizer: NormalizerBase,
        repository: Repository,
    ) -> None:
        self.crawler = crawler
        self.discovery = discovery
        self.normalizer = normalizer
        self.repository = repository

    async def build(
        self,
        seed_url: str,
        *,
        authoritative_crawl: bool = False,
    ) -> list[PageBuildResult]:
        """Build Company Knowledge from one crawl.

        Missing-page reconciliation runs only when the caller explicitly marks
        the crawl as authoritative and every discovered page is processed
        successfully.
        """
        crawl_result = await self.crawler.discover(seed_url)
        page_results: list[PageBuildResult] = []
        seen_urls: set[HttpUrl] = set()

        for discovered_url in crawl_result.urls:
            page = await self.discovery.extract(str(discovered_url.url))
            normalized_page = self.normalizer.normalize(page)

            section_fingerprints = [
                fingerprint_section(section)
                for section in normalized_page.sections
            ]
            page_fingerprint = fingerprint_page(normalized_page)

            save_result = self.repository.save_page(
                normalized_page,
                page_fingerprint,
                section_fingerprints,
            )

            section_changes = self._get_section_changes(
                normalized_page,
                section_fingerprints,
                save_result,
            )

            seen_urls.add(normalized_page.url)
            page_results.append(
                PageBuildResult(
                    url=normalized_page.url,
                    save_result=save_result,
                    section_changes=section_changes,
                )
            )

        if authoritative_crawl:
            self.repository.mark_missing_pages_inactive(seen_urls)

        return page_results

    def _get_section_changes(
        self,
        page: PageDocument,
        section_fingerprints: list[str],
        save_result: SavePageResult,
    ) -> SectionChangeSet | None:
        """Return deterministic section changes for a newly created version."""
        if save_result.status != SavePageStatus.CHANGED:
            return None

        previous_version = self.repository.get_page_version(
            page.url,
            save_result.version_number - 1,
        )
        if previous_version is None:
            raise RuntimeError(
                f"previous version missing for changed page {page.url}"
            )

        current_sections = [
            SectionVersion(
                index=section.index,
                headings=section.headings,
                text=section.text,
                fingerprint=fingerprint,
            )
            for section, fingerprint in zip(
                page.sections,
                section_fingerprints,
                strict=True,
            )
        ]

        return classify_section_changes(
            previous_version.sections,
            current_sections,
        )
