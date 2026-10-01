"""Apply optional semantic interpretation after deterministic page changes."""

import asyncio
from collections.abc import Sequence

from app.modules.company_knowledge.extraction.base import ChangeInterpreter
from app.modules.company_knowledge.models.change_interpretation import (
    InterpretedSectionChange,
    PageChangeInterpretation,
    SectionChangeInput,
)
from app.modules.company_knowledge.models.section_change import SectionChangeSet
from app.modules.company_knowledge.models.version import SavePageStatus
from app.modules.company_knowledge.services.base import PageBuildResult


class ChangeInterpretationError(RuntimeError):
    """Add page and section context to an interpretation failure."""

    def __init__(
        self,
        page_result: PageBuildResult,
        change: SectionChangeInput,
        error: Exception,
    ) -> None:
        indices = []
        if change.previous_section_index is not None:
            indices.append(
                f"previous section {change.previous_section_index}"
            )
        if change.current_section_index is not None:
            indices.append(
                f"current section {change.current_section_index}"
            )

        super().__init__(
            f"failed to interpret {page_result.url} "
            f"version {page_result.save_result.version_number} "
            f"{change.change_type.value} change "
            f"({', '.join(indices)}): "
            f"{type(error).__name__}: {error}"
        )


class CompanyKnowledgeInterpretationService:
    """Interpret deterministic section changes without affecting persistence."""

    def __init__(
        self,
        interpreter: ChangeInterpreter,
        concurrency: int = 5,
    ) -> None:
        if concurrency < 1:
            raise ValueError("concurrency must be at least 1.")

        self.interpreter = interpreter
        self.semaphore = asyncio.Semaphore(concurrency)

    async def interpret(
        self,
        page_results: Sequence[PageBuildResult],
    ) -> list[PageChangeInterpretation]:
        """Interpret changed page results and skip deterministic no-op results."""
        interpretations: list[PageChangeInterpretation] = []

        for page_result in page_results:
            interpretation = await self._interpret_page(page_result)
            if interpretation is not None:
                interpretations.append(interpretation)

        return interpretations

    async def _interpret_page(
        self,
        page_result: PageBuildResult,
    ) -> PageChangeInterpretation | None:
        """Interpret one changed page when it has section-level changes."""
        if page_result.save_result.status != SavePageStatus.CHANGED:
            return None

        if page_result.section_changes is None:
            return None

        change_inputs = self._build_change_inputs(
            page_result.section_changes
        )
        if not change_inputs:
            return None

        outcomes = await asyncio.gather(
            *(
                self._interpret_change(page_result, change)
                for change in change_inputs
            ),
            return_exceptions=True,
        )

        interpreted_changes: list[InterpretedSectionChange] = []
        for outcome in outcomes:
            if isinstance(outcome, Exception):
                raise outcome
            interpreted_changes.append(outcome)

        return PageChangeInterpretation(
            url=page_result.url,
            version_number=page_result.save_result.version_number,
            changes=tuple(interpreted_changes),
        )

    async def _interpret_change(
        self,
        page_result: PageBuildResult,
        change: SectionChangeInput,
    ) -> InterpretedSectionChange:
        """Interpret one change under the shared concurrency limit."""
        async with self.semaphore:
            try:
                narrative = await self.interpreter.interpret(change)
            except Exception as error:
                raise ChangeInterpretationError(
                    page_result,
                    change,
                    error,
                ) from error

        return InterpretedSectionChange(
            change_type=change.change_type,
            previous_section_index=change.previous_section_index,
            current_section_index=change.current_section_index,
            narrative=narrative,
        )

    @staticmethod
    def _build_change_inputs(
        changes: SectionChangeSet,
    ) -> tuple[SectionChangeInput, ...]:
        """Convert deterministic changes into stable interpreter input order."""
        added = tuple(
            SectionChangeInput.from_added(section)
            for section in changes.added
        )
        removed = tuple(
            SectionChangeInput.from_removed(section)
            for section in changes.removed
        )
        changed = tuple(
            SectionChangeInput.from_changed(
                before=section_change.before,
                after=section_change.after,
            )
            for section_change in changes.changed
        )
        return added + removed + changed
