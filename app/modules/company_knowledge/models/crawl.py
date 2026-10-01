"""Pydantic models for website crawl discovery results."""

from enum import Enum

from pydantic import BaseModel, Field, HttpUrl


class CrawlIncompleteReason(str, Enum):
    """Reason a crawl cannot represent the complete reachable site."""

    PAGE_LIMIT_REACHED = "page_limit_reached"
    DEPTH_LIMIT_REACHED = "depth_limit_reached"
    EXTRACTION_FAILED = "extraction_failed"


class DiscoveredURL(BaseModel):
    """One URL discovered during website crawling."""

    url: HttpUrl
    depth: int
    discovered_from: HttpUrl | None = None


class CrawlResult(BaseModel):
    """Discovered URLs and evidence about crawl completeness."""

    seed_url: HttpUrl
    urls: list[DiscoveredURL] = Field(default_factory=list)
    visited_count: int = 0
    skipped_count: int = 0
    incomplete_reasons: set[CrawlIncompleteReason] = Field(default_factory=set)

    @property
    def is_complete(self) -> bool:
        """Return whether discovery found no evidence of a partial crawl."""
        return not self.incomplete_reasons
