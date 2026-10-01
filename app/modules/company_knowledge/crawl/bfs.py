"""Bounded breadth-first crawl strategy."""

import asyncio
from urllib.parse import urlsplit, urlunsplit

from app.modules.company_knowledge.crawl.base import CrawlStrategy
from app.modules.company_knowledge.crawl.link_extractor import LinkExtractor
from app.modules.company_knowledge.crawl.preprocess_url import preprocess_url
from app.modules.company_knowledge.crawl.validation import (
    is_crawlable_url,
    normalize_host,
)
from app.modules.company_knowledge.models.crawl import (
    CrawlIncompleteReason,
    CrawlResult,
    DiscoveredURL,
)


class BFSCrawlStrategy(CrawlStrategy):
    """Discover internal website URLs using breadth-first traversal."""

    def __init__(
        self,
        link_extractor: LinkExtractor,
        max_pages: int = 100,
        max_depth: int = 5,
        concurrency: int = 5,
    ) -> None:
        if max_pages < 1:
            raise ValueError("max_pages must be at least 1.")

        if max_depth < 0:
            raise ValueError("max_depth cannot be negative.")

        if concurrency < 1:
            raise ValueError("concurrency must be at least 1.")

        self.link_extractor = link_extractor
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.semaphore = asyncio.Semaphore(concurrency)

    async def _extract_links(self, url: str) -> list[str]:
        """Run one link-extraction task under the crawl concurrency limit."""
        async with self.semaphore:
            return await self.link_extractor.extract(url)

    def _dedupe_key(self, url: str) -> str:
        """Build a stable key for equivalent crawl URLs."""
        parsed_url = urlsplit(url)
        host = normalize_host(parsed_url.hostname or "")

        netloc = host

        if parsed_url.port is not None:
            netloc = f"{host}:{parsed_url.port}"

        return urlunsplit(
            (
                parsed_url.scheme.lower(),
                netloc,
                parsed_url.path,
                parsed_url.query,
                "",
            )
        )

    def _has_unvisited_crawlable_link(
        self,
        source_url: str,
        hrefs: list[str],
        seed_url: str,
        seen: set[str],
    ) -> bool:
        """Return whether a depth limit hides an eligible new URL."""
        for href in hrefs:
            url = preprocess_url(source_url, href)
            if not is_crawlable_url(url, seed_url):
                continue
            if self._dedupe_key(url) not in seen:
                return True

        return False

    async def discover(self, seed_url: str) -> CrawlResult:
        """Discover internal URLs level by level from the seed URL."""
        normalized_seed_url = preprocess_url(seed_url, seed_url)

        seed = DiscoveredURL(
            url=normalized_seed_url,
            depth=0,
            discovered_from=None,
        )

        discovered_urls = [seed]
        current_level = [seed]
        seen = {
            self._dedupe_key(str(seed.url)),
        }

        visited_count = 0
        skipped_count = 0
        incomplete_reasons: set[CrawlIncompleteReason] = set()

        while current_level:
            results = await asyncio.gather(
                *[
                    self._extract_links(str(item.url))
                    for item in current_level
                ],
                return_exceptions=True,
            )

            next_level: list[DiscoveredURL] = []

            for item, result in zip(current_level, results):
                if isinstance(result, BaseException):
                    skipped_count += 1
                    incomplete_reasons.add(
                        CrawlIncompleteReason.EXTRACTION_FAILED
                    )
                    continue

                visited_count += 1

                if item.depth >= self.max_depth:
                    if self._has_unvisited_crawlable_link(
                        str(item.url),
                        result,
                        normalized_seed_url,
                        seen,
                    ):
                        incomplete_reasons.add(
                            CrawlIncompleteReason.DEPTH_LIMIT_REACHED
                        )
                    continue

                next_depth = item.depth + 1

                for href in result:
                    url = preprocess_url(
                        str(item.url),
                        href,
                    )

                    if not is_crawlable_url(
                        url,
                        normalized_seed_url,
                    ):
                        skipped_count += 1
                        continue

                    dedupe_key = self._dedupe_key(url)

                    if dedupe_key in seen:
                        skipped_count += 1
                        continue

                    if len(discovered_urls) >= self.max_pages:
                        skipped_count += 1
                        incomplete_reasons.add(
                            CrawlIncompleteReason.PAGE_LIMIT_REACHED
                        )
                        continue

                    discovered_url = DiscoveredURL(
                        url=url,
                        depth=next_depth,
                        discovered_from=item.url,
                    )

                    seen.add(dedupe_key)
                    discovered_urls.append(discovered_url)
                    next_level.append(discovered_url)

            current_level = next_level

        return CrawlResult(
            seed_url=normalized_seed_url,
            urls=discovered_urls,
            visited_count=visited_count,
            skipped_count=skipped_count,
            incomplete_reasons=incomplete_reasons,
        )
