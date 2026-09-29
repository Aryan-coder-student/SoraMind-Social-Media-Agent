"""Tests for deterministic normalized-content fingerprints."""

import pytest

from app.modules.company_knowledge.fingerprint.sha256 import (
    fingerprint_page,
    fingerprint_section,
)
from app.modules.company_knowledge.models.page import (
    Heading,
    PageDocument,
    PageSection,
)


def make_section(
    *,
    index: int = 0,
    section_id: str | None = "platform",
    classes: list[str] | None = None,
    headings: list[Heading] | None = None,
    text: str = "Stable normalized content",
    child_count: int = 2,
) -> PageSection:
    """Build a normalized section with overridable factual fields."""
    return PageSection(
        index=index,
        id=section_id,
        classes=classes if classes is not None else ["content", "dark"],
        headings=(
            headings
            if headings is not None
            else [Heading(level=2, text="Platform")]
        ),
        text=text,
        child_count=child_count,
    )


def make_page(
    *,
    url: str = "https://example.com/page",
    title: str | None = "Example",
    meta_description: str | None = "Example description",
    canonical_url: str | None = "https://example.com/canonical",
    sections: list[PageSection] | None = None,
) -> PageDocument:
    """Build a normalized page with overridable content and identity fields."""
    return PageDocument(
        url=url,
        title=title,
        meta_description=meta_description,
        canonical_url=canonical_url,
        sections=sections if sections is not None else [make_section()],
    )


def test_same_section_content_has_same_fingerprint() -> None:
    assert fingerprint_section(make_section()) == fingerprint_section(
        make_section()
    )


def test_section_text_change_changes_fingerprint() -> None:
    original = make_section(text="Original")
    changed = make_section(text="Changed")

    assert fingerprint_section(original) != fingerprint_section(changed)


def test_heading_text_change_changes_section_fingerprint() -> None:
    original = make_section(headings=[Heading(level=2, text="Original")])
    changed = make_section(headings=[Heading(level=2, text="Changed")])

    assert fingerprint_section(original) != fingerprint_section(changed)


def test_heading_level_change_changes_section_fingerprint() -> None:
    original = make_section(headings=[Heading(level=2, text="Heading")])
    changed = make_section(headings=[Heading(level=3, text="Heading")])

    assert fingerprint_section(original) != fingerprint_section(changed)


def test_heading_order_change_changes_section_fingerprint() -> None:
    first = Heading(level=2, text="First")
    second = Heading(level=3, text="Second")

    assert fingerprint_section(
        make_section(headings=[first, second])
    ) != fingerprint_section(make_section(headings=[second, first]))


def test_whitespace_change_is_not_normalized_by_fingerprinting() -> None:
    assert fingerprint_section(
        make_section(text="Normalized text")
    ) != fingerprint_section(make_section(text="Normalized text "))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("index", 99),
        ("id", "redesigned-id"),
        ("classes", ["redesigned", "layout"]),
        ("child_count", 99),
    ],
)
def test_dom_metadata_change_does_not_change_section_fingerprint(
    field: str,
    value: object,
) -> None:
    original = make_section()
    changed = original.model_copy(update={field: value})

    assert fingerprint_section(original) == fingerprint_section(changed)


def test_section_fingerprint_is_lowercase_sha256() -> None:
    result = fingerprint_section(make_section())

    assert len(result) == 64
    assert all(character in "0123456789abcdef" for character in result)


def test_same_page_content_has_same_fingerprint() -> None:
    assert fingerprint_page(make_page()) == fingerprint_page(make_page())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("title", "Changed title"),
        ("meta_description", "Changed description"),
    ],
)
def test_page_metadata_change_changes_fingerprint(
    field: str,
    value: str,
) -> None:
    original = make_page()
    changed = original.model_copy(update={field: value})

    assert fingerprint_page(original) != fingerprint_page(changed)


def test_section_change_changes_page_fingerprint() -> None:
    original = make_page(sections=[make_section(text="Original")])
    changed = make_page(sections=[make_section(text="Changed")])

    assert fingerprint_page(original) != fingerprint_page(changed)


def test_section_order_change_changes_page_fingerprint() -> None:
    first = make_section(index=0, text="First")
    second = make_section(index=1, text="Second")
    original = make_page(sections=[first, second])
    reordered = make_page(sections=[second, first])

    assert fingerprint_page(original) != fingerprint_page(reordered)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("url", "https://example.com/moved"),
        ("canonical_url", "https://example.com/new-canonical"),
    ],
)
def test_page_location_change_does_not_change_fingerprint(
    field: str,
    value: str,
) -> None:
    original = make_page()
    changed = original.model_copy(update={field: value})

    assert fingerprint_page(original) == fingerprint_page(changed)


def test_page_fingerprint_is_lowercase_sha256() -> None:
    result = fingerprint_page(make_page())

    assert len(result) == 64
    assert all(character in "0123456789abcdef" for character in result)
