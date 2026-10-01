"""Discover, normalize, fingerprint, and persist one Company Knowledge page."""

from app.modules.company_knowledge.discovery.base import PageDiscoveryBase
from app.modules.company_knowledge.fingerprint.sha256 import (
    fingerprint_page,
    fingerprint_section,
)
from app.modules.company_knowledge.normalization.base import NormalizerBase
from app.modules.company_knowledge.services.base import ProcessedPage
from app.repository.base import Repository


class CompanyKnowledgeDiscoveryService:
    """Process one discovered URL into persisted normalized page state."""

    def __init__(
        self,
        discovery: PageDiscoveryBase,
        normalizer: NormalizerBase,
        repository: Repository,
    ) -> None:
        self.discovery = discovery
        self.normalizer = normalizer
        self.repository = repository

    async def process(self, url: str) -> ProcessedPage:
        """Extract, normalize, fingerprint, and persist one page."""
        page = await self.discovery.extract(url)
        normalized_page = self.normalizer.normalize(page)

        section_fingerprints = tuple(
            fingerprint_section(section)
            for section in normalized_page.sections
        )
        page_fingerprint = fingerprint_page(normalized_page)

        save_result = self.repository.save_page(
            normalized_page,
            page_fingerprint,
            list(section_fingerprints),
        )

        processed_page = ProcessedPage(
            page=normalized_page,
            save_result=save_result,
            section_fingerprints=section_fingerprints,
        )
        return processed_page
