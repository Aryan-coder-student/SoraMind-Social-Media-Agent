"""Company Knowledge errors."""

from pydantic import HttpUrl, ValidationError

from app.modules.company_knowledge.models.change_summary import SectionChangeContext


class InvalidChangeSummaryError(ValueError):
    """Raised when an LLM response is not a valid change summary."""

    def __init__(
        self,
        change: SectionChangeContext,
        validation_error: ValidationError,
    ) -> None:
        section_index = (
            change.current_section_index
            if change.current_section_index is not None
            else change.previous_section_index
        )
        super().__init__(
            f"invalid LLM summary for "
            f"{change.change_type.value} section {section_index}: "
            f"{validation_error}"
        )


class ChangeSummaryError(RuntimeError):
    """Add page and section context to a change-summary failure."""

    def __init__(
        self,
        url: HttpUrl,
        version_number: int,
        change: SectionChangeContext,
        error: Exception,
    ) -> None:
        indices: list[str] = []
        if change.previous_section_index is not None:
            indices.append(
                f"previous section {change.previous_section_index}"
            )
        if change.current_section_index is not None:
            indices.append(
                f"current section {change.current_section_index}"
            )

        super().__init__(
            f"failed to summarize {url} "
            f"version {version_number} "
            f"{change.change_type.value} change "
            f"({', '.join(indices)}): "
            f"{type(error).__name__}: {error}"
        )
