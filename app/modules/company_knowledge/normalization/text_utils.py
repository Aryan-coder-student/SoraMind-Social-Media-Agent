"""Utility functions for normalizing webpage text and sections."""

from app.modules.company_knowledge.models.page import Heading, PageSection
from app.modules.company_knowledge.normalization.text_cleaner import TextCleaner


def clean_unwanted_space(text: str) -> str:
    """Collapse repeated spaces and remove unnecessary blank lines."""
    lines = [
        " ".join(line.split())
        for line in text.splitlines()
    ]

    cleaned_text = "\n".join(
        line
        for line in lines
        if line
    )

    return cleaned_text


def clean_text(text: str, text_cleaner: TextCleaner) -> str:
    """Run the common text-cleaning pipeline."""
    text = text_cleaner.clean(text)
    text = clean_unwanted_space(text)

    return text


def clean_heading(
    heading: Heading,
    text_cleaner: TextCleaner,
) -> Heading:
    """Clean heading text while preserving its DOM heading level."""
    cleaned_heading = heading.model_copy(
        update={
            "text": clean_text(
                heading.text,
                text_cleaner,
            ),
        }
    )

    return cleaned_heading


def clean_section(
    section: PageSection,
    text_cleaner: TextCleaner,
) -> PageSection:
    """Clean section text and headings while preserving DOM metadata."""
    headings = [
        clean_heading(heading, text_cleaner)
        for heading in section.headings
    ]
    headings = [
        heading
        for heading in headings
        if heading.text
    ]

    return section.model_copy(
        update={
            "text": clean_text(
                section.text,
                text_cleaner,
            ),
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
