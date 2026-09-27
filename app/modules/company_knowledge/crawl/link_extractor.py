"""Link extraction abstractions used by crawl strategies."""

import asyncio
from abc import ABC, abstractmethod

from app.infrastructure.browser.base import BrowserBase


class LinkExtractor(ABC):
    """Contract for extracting links from one URL."""

    @abstractmethod
    async def extract(self, url: str) -> list[str]:
        """Return links discovered on the given URL."""
        ...


class BrowserLinkExtractor(LinkExtractor):
    """Extract links from rendered pages using the shared browser."""

    def __init__(
        self,
        browser: BrowserBase,
        concurrency: int = 5,
    ) -> None:
        if concurrency < 1:
            raise ValueError("concurrency must be at least 1.")

        self.browser = browser
        self.semaphore = asyncio.Semaphore(concurrency)

    async def extract(self, url: str) -> list[str]:
        """Extract anchor URLs from one rendered page."""
        async with self.semaphore:
            page = await self.browser.new_page()

            try:
                await self.browser.navigate(page, url)

                links = await page.locator("a[href]").evaluate_all(
                    "(elements) => elements.map((element) => element.href)"
                )

                return [
                    str(link)
                    for link in links
                    if link
                ]
            finally:
                await self.browser.close_page(page)
