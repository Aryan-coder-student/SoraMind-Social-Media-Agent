"""Pydantic models for website crawl discovery results."""

from pydantic import BaseModel, Field, HttpUrl


class DiscoveredURL(BaseModel):
    """One URL discovered during website crawling."""

    url: HttpUrl
    depth: int
    discovered_from: HttpUrl | None = None


class CrawlResult(BaseModel):
    """Result of a complete crawl starting from one seed URL."""

    seed_url: HttpUrl
    urls: list[DiscoveredURL] = Field(default_factory=list)
    visited_count: int = 0
    skipped_count: int = 0
