"""Tests for browser-backed link extraction."""

import asyncio
from typing import Any

import pytest

from app.infrastructure.browser.base import BrowserBase
from app.modules.company_knowledge.crawl.link_extractor import BrowserLinkExtractor


class FakeLocator:
    """Return predefined href values."""

    def __init__(self, links: list[Any]) -> None:
        self.links = links

    async def evaluate_all(self, script: str) -> list[Any]:
        assert "element.href" in script
        return self.links


class FakePage:
    """Minimal page object used by BrowserLinkExtractor tests."""

    def __init__(self, links: list[Any]) -> None:
        self.links = links

    def locator(self, selector: str) -> FakeLocator:
        assert selector == "a[href]"
        return FakeLocator(self.links)


class FakeBrowser(BrowserBase):
    """Browser fake that records link-extraction interactions."""

    def __init__(
        self,
        links: list[Any] | None = None,
        fail_navigation: bool = False,
    ) -> None:
        self.links = links or []
        self.fail_navigation = fail_navigation
        self.navigated_urls: list[str] = []
        self.closed_pages: list[FakePage] = []

    async def start(self) -> None:
        pass

    async def new_page(self) -> FakePage:
        return FakePage(self.links)

    async def navigate(self, page: FakePage, url: str) -> None:
        self.navigated_urls.append(url)

        if self.fail_navigation:
            raise RuntimeError("navigation failed")

    async def close_page(self, page: FakePage) -> None:
        self.closed_pages.append(page)

    async def close(self) -> None:
        pass


class TrackingBrowser(FakeBrowser):
    """Track how many navigations run at the same time."""

    def __init__(self) -> None:
        super().__init__(links=[])
        self.active = 0
        self.max_active = 0

    async def navigate(self, page: FakePage, url: str) -> None:
        self.active += 1
        self.max_active = max(self.max_active, self.active)

        await asyncio.sleep(0.01)

        self.active -= 1


@pytest.mark.asyncio
async def test_extracts_links_and_closes_page() -> None:
    browser = FakeBrowser(
        links=[
            "https://example.com/about",
            "",
            None,
        ]
    )
    extractor = BrowserLinkExtractor(
        browser=browser,
        concurrency=2,
    )

    links = await extractor.extract("https://example.com/")

    assert links == ["https://example.com/about"]
    assert browser.navigated_urls == ["https://example.com/"]
    assert len(browser.closed_pages) == 1


@pytest.mark.asyncio
async def test_closes_page_when_navigation_fails() -> None:
    browser = FakeBrowser(fail_navigation=True)
    extractor = BrowserLinkExtractor(browser=browser)

    with pytest.raises(RuntimeError, match="navigation failed"):
        await extractor.extract("https://example.com/")

    assert len(browser.closed_pages) == 1


@pytest.mark.asyncio
async def test_limits_concurrent_browser_extraction() -> None:
    browser = TrackingBrowser()
    extractor = BrowserLinkExtractor(
        browser=browser,
        concurrency=2,
    )

    await asyncio.gather(
        *[
            extractor.extract(f"https://example.com/{index}")
            for index in range(5)
        ]
    )

    assert browser.max_active == 2


def test_rejects_invalid_concurrency() -> None:
    browser = FakeBrowser()

    with pytest.raises(ValueError, match="concurrency"):
        BrowserLinkExtractor(
            browser=browser,
            concurrency=0,
        )
