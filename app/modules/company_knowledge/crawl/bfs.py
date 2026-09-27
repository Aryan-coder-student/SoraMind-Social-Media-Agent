"""Bounded breadth-first crawl strategy."""

import asyncio

from app.modules.company_knowledge.crawl.base import CrawlStrategy
from app.modules.company_knowledge.crawl.link_extractor import LinkExtractor
from app.modules.company_knowledge.crawl.preprocess_url import preprocess_url
from app.modules.company_knowledge.crawl.validation import is_crawlable_url
from app.modules.company_knowledge.models.crawl import CrawlResult, DiscoveredURL


class BFSCrawlStrategy(CrawlStrategy):
    """Discover internal website URLs using breadth-first traversal."""

    def __init__(
        self,
        link_extractor: LinkExtractor,
        max_pages: int = 100,
        max_depth: int = 5,
    ) -> None:
        if max_pages < 1:
            raise ValueError("max_pages must be at least 1.")

        if max_depth < 0:
            raise ValueError("max_depth cannot be negative.")

        self.link_extractor = link_extractor
        self.max_pages = max_pages
        self.max_depth = max_depth

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
        seen = {str(seed.url)}

        visited_count = 0
        skipped_count = 0

        while current_level:
            results = await asyncio.gather(
                *[
                    self.link_extractor.extract(str(item.url))
                    for item in current_level
                ],
                return_exceptions=True,
            )

            next_level: list[DiscoveredURL] = []

            for item, result in zip(current_level, results):
                if isinstance(result, BaseException):
                    skipped_count += 1
                    continue

                visited_count += 1

                if item.depth >= self.max_depth:
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

                    if url in seen:
                        skipped_count += 1
                        continue

                    if len(discovered_urls) >= self.max_pages:
                        skipped_count += 1
                        continue

                    discovered_url = DiscoveredURL(
                        url=url,
                        depth=next_depth,
                        discovered_from=item.url,
                    )

                    seen.add(url)
                    discovered_urls.append(discovered_url)
                    next_level.append(discovered_url)

            current_level = next_level

        return CrawlResult(
            seed_url=normalized_seed_url,
            urls=discovered_urls,
            visited_count=visited_count,
            skipped_count=skipped_count,
        )
