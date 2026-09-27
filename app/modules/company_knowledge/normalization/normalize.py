"""Deterministic normalization for factual webpage content."""

from app.modules.company_knowledge.models.page import (
    Heading,
    PageDocument,
    PageSection,
)
from app.modules.company_knowledge.normalization.base import NormalizerBase
from app.modules.company_knowledge.normalization.text_cleaner import TextCleaner
from app.modules.company_knowledge.normalization.text_utils import (
    clean_unwanted_space,
    remove_empty_sections,
)


class PageNormalizer(NormalizerBase):
    """Normalize factual webpage content before LLM extraction."""

    def __init__(self, text_cleaner: TextCleaner) -> None:
        self.text_cleaner = text_cleaner

    def clean_text(self, text: str) -> str:
        """Clean Unicode noise and normalize whitespace."""
        cleaned_text = self.text_cleaner.clean(text)
        cleaned_text = clean_unwanted_space(cleaned_text)

        return cleaned_text

    def clean_heading(self, heading: Heading) -> Heading:
        """Clean heading text while preserving its DOM heading level."""
        cleaned_heading = heading.model_copy(
            update={
                "text": self.clean_text(heading.text),
            }
        )

        return cleaned_heading

    def clean_section(self, section: PageSection) -> PageSection:
        """Clean section text and headings while preserving DOM metadata."""
        headings = [
            self.clean_heading(heading)
            for heading in section.headings
        ]
        headings = [
            heading
            for heading in headings
            if heading.text
        ]

        cleaned_section = section.model_copy(
            update={
                "text": self.clean_text(section.text),
                "headings": headings,
            }
        )

        return cleaned_section

    def normalize(self, page: PageDocument) -> PageDocument:
        """Return a cleaned copy of the page document."""
        sections = [
            self.clean_section(section)
            for section in page.sections
        ]
        sections = remove_empty_sections(sections)

        title = (
            self.clean_text(page.title)
            if page.title is not None
            else None
        )

        meta_description = (
            self.clean_text(page.meta_description)
            if page.meta_description is not None
            else None
        )

        normalized_page = page.model_copy(
            update={
                "title": title,
                "meta_description": meta_description,
                "sections": sections,
            }
        )

        return normalized_page
