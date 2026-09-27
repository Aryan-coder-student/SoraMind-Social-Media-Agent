"""Base contract and shared cleaning behavior for page normalization."""

from abc import ABC, abstractmethod

from app.modules.company_knowledge.models.page import (
    Heading,
    PageDocument,
    PageSection,
)
from app.modules.company_knowledge.normalization.text_cleaner import TextCleaner
from app.modules.company_knowledge.normalization.text_utils import (
    clean_unwanted_space,
)


class NormalizerBase(ABC):
    """Base contract for deterministic webpage normalization."""

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

    @abstractmethod
    def normalize(self, page: PageDocument) -> PageDocument:
        """Normalize a factual webpage document."""
        ...
