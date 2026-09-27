"""Deterministic normalization for factual webpage content."""

from app.modules.company_knowledge.models.page import PageDocument
from app.modules.company_knowledge.normalization.base import NormalizerBase
from app.modules.company_knowledge.normalization.text_cleaner import (
    TextCleaner,
    UnicodeSanityAdapter,
)
from app.modules.company_knowledge.normalization.text_utils import (
    clean_section,
    clean_text,
    remove_empty_sections,
)


class PageNormalizer(NormalizerBase):
    """Normalize factual webpage content before LLM extraction."""

    def __init__(
        self,
        text_cleaner: TextCleaner | None = None,
    ) -> None:
        self.text_cleaner = (
            text_cleaner
            if text_cleaner is not None
            else UnicodeSanityAdapter()
        )

    def normalize(self, page: PageDocument) -> PageDocument:
        """Return a cleaned copy of the page document."""
        sections = [
            clean_section(
                section,
                self.text_cleaner,
            )
            for section in page.sections
        ]
        sections = remove_empty_sections(sections)

        return page.model_copy(
            update={
                "title": (
                    clean_text(
                        page.title,
                        self.text_cleaner,
                    )
                    if page.title is not None
                    else None
                ),
                "meta_description": (
                    clean_text(
                        page.meta_description,
                        self.text_cleaner,
                    )
                    if page.meta_description is not None
                    else None
                ),
                "sections": sections,
            }
        )
