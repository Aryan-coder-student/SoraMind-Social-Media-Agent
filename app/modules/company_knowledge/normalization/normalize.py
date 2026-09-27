"""Deterministic normalization for factual webpage content."""

from app.modules.company_knowledge.models.page import (
    Heading,
    PageDocument,
    PageSection,
)
from app.modules.company_knowledge.normalization.base import NormalizerBase


def clean_hidden_characters(text: str) -> str:
    """Remove hidden characters that add noise to extracted text."""
    return (
        text.replace("\u200b", "")
        .replace("\ufeff", "")
        .replace("\xa0", " ")
    )


def clean_unwanted_space(text: str) -> str:
    """Collapse repeated spaces and remove unnecessary blank lines."""
    lines = [
        " ".join(line.split())
        for line in text.splitlines()
    ]

    return "\n".join(
        line
        for line in lines
        if line
    )


def clean_text(text: str) -> str:
    """Run the common text-cleaning pipeline."""
    text = clean_hidden_characters(text)
    text = clean_unwanted_space(text)

    return text


def clean_heading(heading: Heading) -> Heading:
    """Clean heading text while preserving its DOM heading level."""
    return heading.model_copy(
        update={
            "text": clean_text(heading.text),
        }
    )


def clean_section(section: PageSection) -> PageSection:
    """Clean section text and headings while preserving DOM metadata."""
    headings = [
        clean_heading(heading)
        for heading in section.headings
    ]
    headings = [
        heading
        for heading in headings
        if heading.text
    ]

    return section.model_copy(
        update={
            "text": clean_text(section.text),
            "headings": headings,
        }
    )


def remove_empty_sections(
    sections: list[PageSection],
) -> list[PageSection]:
    """Remove sections that contain no useful text or headings."""
    return [
        section
        for section in sections
        if section.text or section.headings
    ]


class PageNormalizer(NormalizerBase):
    """Normalize factual webpage content before LLM extraction."""

    def normalize(self, page: PageDocument) -> PageDocument:
        """Return a cleaned copy of the page document."""
        sections = [
            clean_section(section)
            for section in page.sections
        ]
        sections = remove_empty_sections(sections)

        return page.model_copy(
            update={
                "title": (
                    clean_text(page.title)
                    if page.title is not None
                    else None
                ),
                "meta_description": (
                    clean_text(page.meta_description)
                    if page.meta_description is not None
                    else None
                ),
                "sections": sections,
            }
        )
