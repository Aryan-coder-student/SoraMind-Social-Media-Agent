"""Contracts for optional section-change summarization."""

from abc import ABC, abstractmethod

from app.modules.company_knowledge.models.change_summary import (
    ChangeSummary,
    SectionChangeContext,
)


class SectionChangeSummarizer(ABC):
    """Summarize one deterministic section change."""

    @abstractmethod
    async def summarize(
        self,
        change: SectionChangeContext,
    ) -> ChangeSummary:
        """Return a validated summary for one section change."""
        ...
