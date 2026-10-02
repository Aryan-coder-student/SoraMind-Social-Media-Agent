"""Summarize deterministic Company Knowledge section changes."""

import asyncio
from collections.abc import Sequence

from app.modules.company_knowledge.error import ChangeSummaryError
from app.modules.company_knowledge.extraction.base import SectionChangeSummarizer
from app.modules.company_knowledge.models.change_summary import (
    PageChangeSummary,
    SectionChangeContext,
    SectionChangeSummary,
    SectionChangeType,
)
from app.modules.company_knowledge.models.section_change import SectionChangeSet
from app.modules.company_knowledge.models.version import SavePageStatus
from app.modules.company_knowledge.services.base import PageBuildResult


class ChangeSummaryService:
    """Create optional LLM summaries after deterministic change detection."""

    def __init__(
        self,
        summarizer: SectionChangeSummarizer,
        concurrency: int = 5,
    ) -> None:
        if concurrency < 1:
            raise ValueError("concurrency must be at least 1.")

        self.summarizer = summarizer
        self.semaphore = asyncio.Semaphore(concurrency)

    async def summarize(
        self,
        page_results: Sequence[PageBuildResult],
    ) -> list[PageChangeSummary]:
        """Summarize changed pages and skip results with no section changes."""
        summaries: list[PageChangeSummary] = []

        for page_result in page_results:
            page_summary = await self._summarize_page(page_result)
            if page_summary is not None:
                summaries.append(page_summary)

        return summaries

    async def _summarize_page(
        self,
        page_result: PageBuildResult,
    ) -> PageChangeSummary | None:
        """Summarize one changed page when section changes exist."""
        if page_result.save_result.status != SavePageStatus.CHANGED:
            return None

        if page_result.section_changes is None:
            return None

        changes = self._build_change_contexts(page_result.section_changes)
        if not changes:
            return None

        outcomes = await asyncio.gather(
            *(
                self._summarize_change(page_result, change)
                for change in changes
            ),
            return_exceptions=True,
        )

        change_summaries: list[SectionChangeSummary] = []
        for outcome in outcomes:
            if isinstance(outcome, Exception):
                raise outcome
            change_summaries.append(outcome)

        return PageChangeSummary(
            url=page_result.url,
            version_number=page_result.save_result.version_number,
            changes=tuple(change_summaries),
        )

    async def _summarize_change(
        self,
        page_result: PageBuildResult,
        change: SectionChangeContext,
    ) -> SectionChangeSummary:
        """Summarize one section change under the concurrency limit."""
        async with self.semaphore:
            try:
                details = await self.summarizer.summarize(change)
            except Exception as error:
                raise ChangeSummaryError(
                    page_result.url,
                    page_result.save_result.version_number,
                    change,
                    error,
                ) from error

        return SectionChangeSummary(
            change_type=change.change_type,
            previous_section_index=change.previous_section_index,
            current_section_index=change.current_section_index,
            details=details,
        )

    @staticmethod
    def _build_change_contexts(
        changes: SectionChangeSet,
    ) -> tuple[SectionChangeContext, ...]:
        """Convert deterministic changes into stable summarizer input order."""
        contexts: list[SectionChangeContext] = []

        contexts.extend(
            SectionChangeContext(
                change_type=SectionChangeType.ADDED,
                after=section,
            )
            for section in changes.added
        )
        contexts.extend(
            SectionChangeContext(
                change_type=SectionChangeType.REMOVED,
                before=section,
            )
            for section in changes.removed
        )
        contexts.extend(
            SectionChangeContext(
                change_type=SectionChangeType.CHANGED,
                before=section_change.before,
                after=section_change.after,
            )
            for section_change in changes.changed
        )

        return tuple(contexts)
