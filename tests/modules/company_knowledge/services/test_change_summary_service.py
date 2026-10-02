"""Tests for optional Company Knowledge change summaries."""

import asyncio

import pytest
from pydantic import HttpUrl

from app.modules.company_knowledge.error import ChangeSummaryError
from app.modules.company_knowledge.extraction.base import SectionChangeSummarizer
from app.modules.company_knowledge.models.change_summary import (
    ChangeSummary,
    SectionChangeContext,
    SectionChangeType,
)
from app.modules.company_knowledge.models.page import Heading
from app.modules.company_knowledge.models.section_change import (
    SectionChange,
    SectionChangeSet,
)
from app.modules.company_knowledge.models.version import (
    SavePageResult,
    SavePageStatus,
    SectionVersion,
)
from app.modules.company_knowledge.services.base import PageBuildResult
from app.modules.company_knowledge.services.change_summary_service import (
    ChangeSummaryService,
)


class RecordingSummarizer(SectionChangeSummarizer):
    """Record inputs and return deterministic summaries."""

    def __init__(self) -> None:
        self.changes: list[SectionChangeContext] = []
        self.active_calls = 0
        self.maximum_active_calls = 0
        self.error: Exception | None = None

    async def summarize(
        self,
        change: SectionChangeContext,
    ) -> ChangeSummary:
        self.changes.append(change)
        self.active_calls += 1
        self.maximum_active_calls = max(
            self.maximum_active_calls,
            self.active_calls,
        )

        try:
            await asyncio.sleep(0.01)
            if self.error is not None:
                raise self.error
            return ChangeSummary(
                summary=f"Summarized {change.change_type.value} section.",
                category=None,
                key_points=(),
            )
        finally:
            self.active_calls -= 1


class FailingThenCompletingSummarizer(SectionChangeSummarizer):
    """Fail one call while recording completion of a slower sibling call."""

    def __init__(self) -> None:
        self.completed_section_indices: list[int] = []

    async def summarize(
        self,
        change: SectionChangeContext,
    ) -> ChangeSummary:
        assert change.after is not None

        if change.after.index == 1:
            await asyncio.sleep(0.001)
            raise RuntimeError("first provider call failed")

        await asyncio.sleep(0.02)
        self.completed_section_indices.append(change.after.index)
        return ChangeSummary(summary="Second provider call completed.")


def test_rejects_non_positive_concurrency() -> None:
    with pytest.raises(ValueError, match="concurrency must be at least 1"):
        ChangeSummaryService(
            RecordingSummarizer(),
            concurrency=0,
        )


def make_section(index: int, text: str) -> SectionVersion:
    return SectionVersion(
        index=index,
        headings=[Heading(level=2, text=f"Section {index}")],
        text=text,
        fingerprint=str(index) * 64,
    )


def make_result(
    status: SavePageStatus,
    changes: SectionChangeSet | None,
) -> PageBuildResult:
    return PageBuildResult(
        url=HttpUrl("https://example.com/pricing"),
        save_result=SavePageResult(
            status=status,
            version_number=2,
        ),
        section_changes=changes,
    )


@pytest.mark.asyncio
async def test_summarizes_added_removed_and_changed_sections() -> None:
    summarizer = RecordingSummarizer()
    service = ChangeSummaryService(
        summarizer,
        concurrency=2,
    )
    previous_removed = make_section(1, "Legacy plan")
    current_added = make_section(2, "Enterprise plan")
    previous_changed = make_section(3, "Starter plan")
    current_changed = make_section(4, "Starter and Pro plans")
    result = make_result(
        SavePageStatus.CHANGED,
        SectionChangeSet(
            added=(current_added,),
            removed=(previous_removed,),
            changed=(
                SectionChange(
                    before=previous_changed,
                    after=current_changed,
                ),
            ),
        ),
    )

    summaries = await service.summarize([result])

    assert len(summaries) == 1
    page_summary = summaries[0]
    assert str(page_summary.url) == "https://example.com/pricing"
    assert page_summary.version_number == 2
    assert [
        change.change_type for change in page_summary.changes
    ] == [
        SectionChangeType.ADDED,
        SectionChangeType.REMOVED,
        SectionChangeType.CHANGED,
    ]
    assert page_summary.changes[0].previous_section_index is None
    assert page_summary.changes[0].current_section_index == 2
    assert page_summary.changes[1].previous_section_index == 1
    assert page_summary.changes[1].current_section_index is None
    assert page_summary.changes[2].previous_section_index == 3
    assert page_summary.changes[2].current_section_index == 4
    assert summarizer.maximum_active_calls == 2


@pytest.mark.asyncio
async def test_skips_results_without_deterministic_section_changes() -> None:
    summarizer = RecordingSummarizer()
    service = ChangeSummaryService(summarizer)
    section_changes = SectionChangeSet(
        added=(make_section(1, "Unexpected input"),)
    )
    results = [
        make_result(SavePageStatus.NEW, section_changes),
        make_result(SavePageStatus.UNCHANGED, section_changes),
        make_result(SavePageStatus.REACTIVATED, section_changes),
        make_result(SavePageStatus.CHANGED, SectionChangeSet()),
    ]

    summaries = await service.summarize(results)

    assert summaries == []
    assert summarizer.changes == []


@pytest.mark.asyncio
async def test_summarizer_failure_includes_page_and_section_context() -> None:
    summarizer = RecordingSummarizer()
    summarizer.error = RuntimeError("provider unavailable")
    service = ChangeSummaryService(summarizer)
    result = make_result(
        SavePageStatus.CHANGED,
        SectionChangeSet(
            added=(make_section(5, "New product"),),
        ),
    )

    with pytest.raises(
        ChangeSummaryError,
        match=(
            "https://example.com/pricing.*version 2.*added.*"
            "current section 5.*provider unavailable"
        ),
    ):
        await service.summarize([result])


@pytest.mark.asyncio
async def test_waits_for_sibling_calls_before_raising_failure() -> None:
    summarizer = FailingThenCompletingSummarizer()
    service = ChangeSummaryService(summarizer, concurrency=2)
    result = make_result(
        SavePageStatus.CHANGED,
        SectionChangeSet(
            added=(
                make_section(1, "First section"),
                make_section(2, "Second section"),
            ),
        ),
    )

    with pytest.raises(ChangeSummaryError, match="first provider call failed"):
        await service.summarize([result])

    assert summarizer.completed_section_indices == [2]
