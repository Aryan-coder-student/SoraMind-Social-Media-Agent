"""Page discovery contract returning factual page/section models."""

from abc import ABC, abstractmethod

from app.modules.company_knowledge.models.page import PageDocument


class PageDiscoveryBase(ABC):
    """Contract for extracting factual structure from a rendered page."""

    @abstractmethod
    async def extract(self, url: str) -> PageDocument:
        """Extract a factual page document from the given URL."""
        ...
