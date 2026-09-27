"""Company Knowledge page-structure discovery.

This module uses the shared browser infrastructure to inspect a rendered page
and build factual PageDocument/PageSection models. Browser lifecycle and raw
Playwright setup stay in app.infrastructure.browser.
"""

from typing import Any

from app.infrastructure.browser.base import BrowserBase
from app.modules.company_knowledge.discovery.base import PageDiscoveryBase
from app.modules.company_knowledge.models.page import PageDocument, PageSection


SECTION_EVALUATION_SCRIPT = """
(sections) => sections.map((section) => ({
    id: section.id || null,
    classes: Array.from(section.classList),
    headings: Array.from(section.querySelectorAll("h1, h2, h3, h4, h5, h6"))
        .map((heading) => ({
            level: Number(heading.tagName.slice(1)),
            text: heading.innerText,
        })),
    text: section.innerText,
    child_count: section.children.length,
}))
"""


class PageDiscovery(PageDiscoveryBase):
    """Extract factual structure from rendered webpages."""

    def __init__(self, browser: BrowserBase) -> None:
        self.browser = browser

    async def extract(self, url: str) -> PageDocument:
        """Navigate one page and extract its factual DOM structure."""
        page = await self.browser.new_page()

        try:
            await self.browser.navigate(page, url)

            title = await page.title()
            meta_description = await page.locator(
                'meta[name="description"]'
            ).get_attribute("content")
            canonical_url = await page.locator(
                'link[rel="canonical"]'
            ).get_attribute("href")

            section_selector = await self._section_selector(page)
            raw_sections: list[dict[str, Any]] = await page.locator(
                section_selector
            ).evaluate_all(SECTION_EVALUATION_SCRIPT)
            sections = [
                PageSection(index=index, **raw_section)
                for index, raw_section in enumerate(raw_sections)
            ]

            return PageDocument(
                url=page.url,
                title=title or None,
                meta_description=meta_description or None,
                canonical_url=canonical_url or None,
                sections=sections,
            )
        finally:
            await self.browser.close_page(page)

    async def _section_selector(self, page: Any) -> str:
        """Select outermost sections, preferring those inside main."""
        if await page.locator("main").count():
            return "main section:not(section section)"

        return "section:not(section section)"
