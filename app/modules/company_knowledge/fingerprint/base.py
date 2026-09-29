"""Canonical content payloads used by fingerprint algorithms."""

from collections.abc import Sequence

from app.modules.company_knowledge.models.page import PageDocument, PageSection


def section_payload(section: PageSection) -> dict[str, object]:
    """Select meaningful normalized content from one section."""
    return {
        "headings": [
            {
                "level": heading.level,
                "text": heading.text,
            }
            for heading in section.headings
        ],
        "text": section.text,
    }


def page_payload(
    page: PageDocument,
    section_fingerprints: Sequence[str],
) -> dict[str, object]:
    """Select meaningful normalized content from one page."""
    return {
        "title": page.title,
        "meta_description": page.meta_description,
        "sections": list(section_fingerprints),
    }
