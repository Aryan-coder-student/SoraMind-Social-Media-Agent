"""Tests for optional Company Knowledge change interpretation."""

import asyncio

import pytest
from pydantic import HttpUrl

from app.modules.company_knowledge.extraction.base import ChangeInterpreter
from app.modules.company_knowledge.models.change_interpretation import (
    ChangeNarrative,
    SectionChangeInput,
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
from app.modules.company_knowledge.services.interpretation_service import (
    ChangeInterpretationError,
    CompanyKnowledgeInterpretationService,
)


class RecordingInterpreter(ChangeInterpreter):
    """Record change inputs and return deterministic narratives."""

    def __init__(self) -> None:
        self.changes: list[SectionChangeInput] = []
        self.active_calls = 0
        self.maximum_active_calls = 0
        self.error: Exception | None = None

    async def interpret(
        self,
        change: SectionChangeInput,
    ) -> ChangeNarrative:
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
            return ChangeNarrative(
                summary=f"Interpreted {change.change_type.value} section.",
                semantic_label=None,
                key_points=(),
            )
        finally:
            self.active_calls -= 1


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
async def test_interprets_added_removed_and_changed_sections() -> None:
    interpreter = RecordingInterpreter()
    service = CompanyKnowledgeInterpretationService(
        interpreter,
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

    interpretations = await service.interpret([result])

    assert len(interpretations) == 1
    page_interpretation = interpretations[0]
    assert str(page_interpretation.url) == "https://example.com/pricing"
    assert page_interpretation.version_number == 2
    assert [
        change.change_type for change in page_interpretation.changes
    ] == [
        SectionChangeType.ADDED,
        SectionChangeType.REMOVED,
        SectionChangeType.CHANGED,
    ]
    assert page_interpretation.changes[0].previous_section_index is None
    assert page_interpretation.changes[0].current_section_index == 2
    assert page_interpretation.changes[1].previous_section_index == 1
    assert page_interpretation.changes[1].current_section_index is None
    assert page_interpretation.changes[2].previous_section_index == 3
    assert page_interpretation.changes[2].current_section_index == 4
    assert interpreter.maximum_active_calls == 2


@pytest.mark.asyncio
async def test_skips_results_without_deterministic_section_changes() -> None:
    interpreter = RecordingInterpreter()
    service = CompanyKnowledgeInterpretationService(interpreter)
    section_changes = SectionChangeSet(
        added=(make_section(1, "Unexpected input"),)
    )
    results = [
        make_result(SavePageStatus.NEW, section_changes),
        make_result(SavePageStatus.UNCHANGED, section_changes),
        make_result(SavePageStatus.REACTIVATED, section_changes),
        make_result(SavePageStatus.CHANGED, SectionChangeSet()),
    ]

    interpretations = await service.interpret(results)

    assert interpretations == []
    assert interpreter.changes == []


@pytest.mark.asyncio
async def test_interpreter_failure_includes_page_and_section_context() -> None:
    interpreter = RecordingInterpreter()
    interpreter.error = RuntimeError("provider unavailable")
    service = CompanyKnowledgeInterpretationService(interpreter)
    result = make_result(
        SavePageStatus.CHANGED,
        SectionChangeSet(
            added=(make_section(5, "New product"),),
        ),
    )

    with pytest.raises(
        ChangeInterpretationError,
        match=(
            "https://example.com/pricing.*version 2.*added.*"
            "current section 5.*provider unavailable"
        ),
    ):
        await service.interpret([result])
