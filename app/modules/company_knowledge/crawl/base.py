"""Crawl strategy contract."""

from abc import ABC, abstractmethod

from app.modules.company_knowledge.models.crawl import CrawlResult


class CrawlStrategy(ABC):
    """Contract for discovering URLs from a website."""

    @abstractmethod
    async def discover(self, seed_url: str) -> CrawlResult:
        """Discover crawlable URLs starting from the seed URL."""
        ...
