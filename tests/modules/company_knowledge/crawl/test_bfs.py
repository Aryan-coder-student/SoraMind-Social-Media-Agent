"""Tests for the bounded breadth-first crawl strategy."""

import pytest

from app.modules.company_knowledge.crawl.bfs import BFSCrawlStrategy
from app.modules.company_knowledge.crawl.link_extractor import LinkExtractor


class FakeLinkExtractor(LinkExtractor):
    """Return predefined links for crawler tests."""

    def __init__(
        self,
        links_by_url: dict[str, list[str] | Exception],
    ) -> None:
        self.links_by_url = links_by_url

    async def extract(self, url: str) -> list[str]:
        result = self.links_by_url.get(url, [])

        if isinstance(result, Exception):
            raise result

        return result


@pytest.mark.asyncio
async def test_discovers_urls_in_breadth_first_order() -> None:
    extractor = FakeLinkExtractor(
        {
            "https://example.com/": [
                "/about",
                "/products",
                "/about",
                "https://external.example/page",
            ],
            "https://example.com/about": ["/team"],
            "https://example.com/products": ["/team"],
            "https://example.com/team": [],
        }
    )
    crawler = BFSCrawlStrategy(
        link_extractor=extractor,
        max_pages=10,
        max_depth=3,
    )

    result = await crawler.discover("https://example.com")

    urls = [str(item.url) for item in result.urls]
    depths = [item.depth for item in result.urls]

    assert urls == [
        "https://example.com/",
        "https://example.com/about",
        "https://example.com/products",
        "https://example.com/team",
    ]
    assert depths == [0, 1, 1, 2]
    assert result.visited_count == 4
    assert result.skipped_count == 3


@pytest.mark.asyncio
async def test_respects_max_pages() -> None:
    extractor = FakeLinkExtractor(
        {
            "https://example.com/": [
                "/about",
                "/products",
                "/contact",
            ],
            "https://example.com/about": [],
        }
    )
    crawler = BFSCrawlStrategy(
        link_extractor=extractor,
        max_pages=2,
        max_depth=5,
    )

    result = await crawler.discover("https://example.com/")

    urls = [str(item.url) for item in result.urls]

    assert urls == [
        "https://example.com/",
        "https://example.com/about",
    ]
    assert result.visited_count == 2


@pytest.mark.asyncio
async def test_respects_max_depth() -> None:
    extractor = FakeLinkExtractor(
        {
            "https://example.com/": ["/about"],
            "https://example.com/about": ["/team"],
        }
    )
    crawler = BFSCrawlStrategy(
        link_extractor=extractor,
        max_pages=10,
        max_depth=1,
    )

    result = await crawler.discover("https://example.com/")

    urls = [str(item.url) for item in result.urls]

    assert urls == [
        "https://example.com/",
        "https://example.com/about",
    ]
    assert result.visited_count == 2


@pytest.mark.asyncio
async def test_page_failure_does_not_stop_crawl() -> None:
    extractor = FakeLinkExtractor(
        {
            "https://example.com/": [
                "/broken",
                "/working",
            ],
            "https://example.com/broken": RuntimeError("page failed"),
            "https://example.com/working": [],
        }
    )
    crawler = BFSCrawlStrategy(
        link_extractor=extractor,
        max_pages=10,
        max_depth=2,
    )

    result = await crawler.discover("https://example.com/")

    assert result.visited_count == 2
    assert result.skipped_count == 1
    assert [str(item.url) for item in result.urls] == [
        "https://example.com/",
        "https://example.com/broken",
        "https://example.com/working",
    ]


def test_rejects_invalid_limits() -> None:
    extractor = FakeLinkExtractor({})

    with pytest.raises(ValueError, match="max_pages"):
        BFSCrawlStrategy(
            link_extractor=extractor,
            max_pages=0,
        )

    with pytest.raises(ValueError, match="max_depth"):
        BFSCrawlStrategy(
            link_extractor=extractor,
            max_depth=-1,
        )
