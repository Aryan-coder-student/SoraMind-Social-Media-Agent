"""Deterministic normalization for factual webpage content."""

from app.modules.company_knowledge.models.page import PageDocument
from app.modules.company_knowledge.normalization.base import NormalizerBase
from app.modules.company_knowledge.normalization.text_utils import (
    remove_empty_sections,
)


class PageNormalizer(NormalizerBase):
    """Normalize factual webpage content before LLM extraction."""

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
