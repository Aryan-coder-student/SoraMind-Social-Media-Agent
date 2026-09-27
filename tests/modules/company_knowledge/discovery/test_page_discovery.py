"""Tests for factual rendered-page discovery."""

from typing import Any

import pytest

from app.infrastructure.browser.base import BrowserBase
from app.modules.company_knowledge.discovery.base import PageDiscoveryBase
from app.modules.company_knowledge.discovery.page_discovery import PageDiscovery


class FakeLocator:
    """Small locator fake supporting the page-discovery operations."""

    def __init__(
        self,
        *,
        attribute: str | None = None,
        count: int = 0,
        sections: list[dict[str, Any]] | None = None,
        evaluation_error: Exception | None = None,
        page: "FakePage | None" = None,
    ) -> None:
        self.attribute = attribute
        self.element_count = count
        self.sections = sections
        self.evaluation_error = evaluation_error
        self.page = page

    async def get_attribute(self, name: str) -> str | None:
        assert name in {"content", "href"}
        return self.attribute

    async def count(self) -> int:
        return self.element_count

    async def evaluate_all(self, script: str) -> list[dict[str, Any]]:
        if self.page is not None:
            self.page.section_evaluation_count += 1
            self.page.section_evaluation_script = script

        if self.evaluation_error is not None:
            raise self.evaluation_error

        return self.sections or []


class FakePage:
    """Rendered-page fake with selector-specific factual data."""

    def __init__(
        self,
        *,
        url: str = "https://example.com/final",
        title: str = "Example title",
        meta_description: str | None = "Example description",
        canonical_url: str | None = "https://example.com/canonical",
        has_main: bool = True,
        sections: list[dict[str, Any]] | None = None,
        evaluation_error: Exception | None = None,
    ) -> None:
        self.url = url
        self.title_value = title
        self.meta_description = meta_description
        self.canonical_url = canonical_url
        self.has_main = has_main
        self.sections = sections or []
        self.evaluation_error = evaluation_error
        self.section_evaluation_count = 0
        self.section_evaluation_script: str | None = None
        self.section_selector: str | None = None

    async def title(self) -> str:
        return self.title_value

    def locator(self, selector: str) -> FakeLocator:
        if selector == 'meta[name="description"]':
            return FakeLocator(attribute=self.meta_description)

        if selector == 'link[rel="canonical"]':
            return FakeLocator(attribute=self.canonical_url)

        if selector == "main":
            return FakeLocator(count=int(self.has_main))

        expected_section_selector = (
            "main section:not(section section)"
            if self.has_main
            else "section:not(section section)"
        )

        if selector == expected_section_selector:
            self.section_selector = selector
            return FakeLocator(
                sections=self.sections,
                evaluation_error=self.evaluation_error,
                page=self,
            )

        raise AssertionError(f"Unexpected selector: {selector}")


class FakeBrowser(BrowserBase):
    """Browser fake that exposes lifecycle calls for assertions."""

    def __init__(
        self,
        page: FakePage,
        navigation_error: Exception | None = None,
    ) -> None:
        self.page = page
        self.navigation_error = navigation_error
        self.start_calls = 0
        self.new_page_calls = 0
        self.navigate_calls: list[tuple[FakePage, str]] = []
        self.close_page_calls: list[FakePage] = []
        self.close_calls = 0

    async def start(self) -> None:
        self.start_calls += 1

    async def new_page(self) -> FakePage:
        self.new_page_calls += 1
        return self.page

    async def navigate(self, page: FakePage, url: str) -> None:
        self.navigate_calls.append((page, url))

        if self.navigation_error is not None:
            raise self.navigation_error

    async def close_page(self, page: FakePage) -> None:
        self.close_page_calls.append(page)

    async def close(self) -> None:
        self.close_calls += 1


def section(
    *,
    element_id: str | None = "platform",
    classes: list[str] | None = None,
    headings: list[dict[str, Any]] | None = None,
    text: str = "Platform details",
    child_count: int = 2,
) -> dict[str, Any]:
    """Build raw factual section data returned by DOM evaluation."""
    return {
        "id": element_id,
        "classes": classes or [],
        "headings": headings or [],
        "text": text,
        "child_count": child_count,
    }


def test_page_discovery_contract_exists() -> None:
    assert PageDiscoveryBase.__abstractmethods__ == {"extract"}
    assert issubclass(PageDiscovery, PageDiscoveryBase)


@pytest.mark.asyncio
async def test_extracts_page_and_section_facts() -> None:
    raw_sections = [
        section(
            classes=["section", "dark"],
            headings=[
                {"level": level, "text": f"Heading {level}"}
                for level in range(1, 7)
            ],
            child_count=4,
        ),
        section(
            element_id="pricing",
            text="Pricing details",
            child_count=1,
        ),
    ]
    page = FakePage(sections=raw_sections)
    browser = FakeBrowser(page)

    document = await PageDiscovery(browser).extract("https://example.com/start")

    assert str(document.url) == "https://example.com/final"
    assert document.title == "Example title"
    assert document.meta_description == "Example description"
    assert str(document.canonical_url) == "https://example.com/canonical"
    assert [item.index for item in document.sections] == [0, 1]
    assert document.sections[0].id == "platform"
    assert document.sections[0].classes == ["section", "dark"]
    assert [heading.level for heading in document.sections[0].headings] == [
        1,
        2,
        3,
        4,
        5,
        6,
    ]
    assert [heading.text for heading in document.sections[0].headings] == [
        f"Heading {level}"
        for level in range(1, 7)
    ]
    assert document.sections[0].text == "Platform details"
    assert document.sections[0].child_count == 4
    assert document.sections[1].id == "pricing"


@pytest.mark.asyncio
@pytest.mark.parametrize("missing_value", [None, ""])
async def test_missing_optional_page_metadata_returns_none(
    missing_value: str | None,
) -> None:
    page = FakePage(
        title="",
        meta_description=missing_value,
        canonical_url=missing_value,
    )

    document = await PageDiscovery(FakeBrowser(page)).extract(
        "https://example.com"
    )

    assert document.title is None
    assert document.meta_description is None
    assert document.canonical_url is None


@pytest.mark.asyncio
async def test_uses_outermost_sections_under_main() -> None:
    page = FakePage(
        sections=[
            section(element_id="platform"),
            section(element_id="pricing"),
        ]
    )

    document = await PageDiscovery(FakeBrowser(page)).extract(
        "https://example.com"
    )

    assert [item.id for item in document.sections] == ["platform", "pricing"]
    assert page.section_selector == "main section:not(section section)"
    assert page.section_evaluation_count == 1


@pytest.mark.asyncio
async def test_falls_back_to_outermost_document_sections_without_main() -> None:
    page = FakePage(
        has_main=False,
        sections=[section(element_id="fallback")],
    )

    document = await PageDiscovery(FakeBrowser(page)).extract(
        "https://example.com"
    )

    assert [item.id for item in document.sections] == ["fallback"]
    assert page.section_selector == "section:not(section section)"


@pytest.mark.asyncio
async def test_preserves_empty_section_and_heading_text() -> None:
    page = FakePage(
        sections=[
            section(
                element_id=None,
                headings=[{"level": 2, "text": ""}],
                text="",
                child_count=0,
            )
        ]
    )

    document = await PageDiscovery(FakeBrowser(page)).extract(
        "https://example.com"
    )

    assert len(document.sections) == 1
    assert document.sections[0].text == ""
    assert document.sections[0].headings[0].text == ""


@pytest.mark.asyncio
async def test_closes_page_after_success_without_managing_browser_lifecycle() -> None:
    page = FakePage()
    browser = FakeBrowser(page)

    await PageDiscovery(browser).extract("https://example.com")

    assert browser.new_page_calls == 1
    assert browser.navigate_calls == [(page, "https://example.com")]
    assert browser.close_page_calls == [page]
    assert browser.start_calls == 0
    assert browser.close_calls == 0


@pytest.mark.asyncio
async def test_closes_page_when_navigation_fails() -> None:
    page = FakePage()
    browser = FakeBrowser(page, navigation_error=RuntimeError("navigation failed"))

    with pytest.raises(RuntimeError, match="navigation failed"):
        await PageDiscovery(browser).extract("https://example.com")

    assert browser.close_page_calls == [page]
    assert browser.start_calls == 0
    assert browser.close_calls == 0


@pytest.mark.asyncio
async def test_closes_page_when_dom_extraction_fails() -> None:
    page = FakePage(evaluation_error=RuntimeError("DOM extraction failed"))
    browser = FakeBrowser(page)

    with pytest.raises(RuntimeError, match="DOM extraction failed"):
        await PageDiscovery(browser).extract("https://example.com")

    assert browser.close_page_calls == [page]
    assert browser.start_calls == 0
    assert browser.close_calls == 0
