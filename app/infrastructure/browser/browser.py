"""Shared async Playwright browser implementation."""

from playwright.async_api import (
    Browser as PlaywrightBrowser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

from .base import BrowserBase


class Browser(BrowserBase):
    """Manage one Playwright browser/context and multiple concurrent pages."""

    def __init__(
        self,
        headless: bool = True,
        navigation_timeout_ms: int = 30_000,
    ) -> None:
        self.headless = headless
        self.navigation_timeout_ms = navigation_timeout_ms

        self._playwright: Playwright | None = None
        self._browser: PlaywrightBrowser | None = None
        self._context: BrowserContext | None = None

    async def start(self) -> None:
        """Start Playwright, Chromium, and a reusable browser context."""
        if self._context is not None:
            return

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
        )
        self._context = await self._browser.new_context()

    async def new_page(self) -> Page:
        """Create a new page so callers can scrape URLs in parallel."""
        if self._context is None:
            raise RuntimeError("Browser is not started. Call start() first.")

        return await self._context.new_page()

    async def navigate(self, page: Page, url: str) -> None:
        """Navigate a page and wait until the initial DOM is ready."""
        await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=self.navigation_timeout_ms,
        )

    async def close_page(self, page: Page) -> None:
        """Close one page without affecting other parallel pages."""
        if not page.is_closed():
            await page.close()

    async def _close_context(self) -> None:
        """Close the shared browser context if it exists."""
        if self._context is not None:
            await self._context.close()
            self._context = None

    async def _close_browser(self) -> None:
        """Close the Chromium browser if it exists."""
        if self._browser is not None:
            await self._browser.close()
            self._browser = None

    async def _stop_playwright(self) -> None:
        """Stop the Playwright runtime if it exists."""
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None

    async def close(self) -> None:
        """Close all shared Playwright resources."""
        await self._close_context()
        await self._close_browser()
        await self._stop_playwright()
