"""Typed inputs and outputs for optional LLM change interpretation."""

from enum import Enum
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from app.modules.company_knowledge.models.version import SectionVersion


NonEmptyText = Annotated[str, Field(min_length=1)]


class SectionChangeType(str, Enum):
    """Deterministic kind of section change supplied to an interpreter."""

    ADDED = "added"
    REMOVED = "removed"
    CHANGED = "changed"


class SectionChangeInput(BaseModel):
    """One deterministic section change ready for semantic interpretation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    change_type: SectionChangeType
    before: SectionVersion | None = None
    after: SectionVersion | None = None

    @classmethod
    def from_added(cls, section: SectionVersion) -> Self:
        """Build an input for a newly added section."""
        return cls(
            change_type=SectionChangeType.ADDED,
            after=section,
        )

    @classmethod
    def from_removed(cls, section: SectionVersion) -> Self:
        """Build an input for a removed section."""
        return cls(
            change_type=SectionChangeType.REMOVED,
            before=section,
        )

    @classmethod
    def from_changed(
        cls,
        *,
        before: SectionVersion,
        after: SectionVersion,
    ) -> Self:
        """Build an input for a section whose content changed."""
        return cls(
            change_type=SectionChangeType.CHANGED,
            before=before,
            after=after,
        )

    @property
    def previous_section_index(self) -> int | None:
        """Return the previous section index when one exists."""
        return self.before.index if self.before is not None else None

    @property
    def current_section_index(self) -> int | None:
        """Return the current section index when one exists."""
        return self.after.index if self.after is not None else None

    @model_validator(mode="after")
    def validate_versions_for_change_type(self) -> Self:
        """Require the before/after versions implied by the change type."""
        expected_presence = {
            SectionChangeType.ADDED: (False, True),
            SectionChangeType.REMOVED: (True, False),
            SectionChangeType.CHANGED: (True, True),
        }
        expected_before, expected_after = expected_presence[self.change_type]
        actual_presence = (self.before is not None, self.after is not None)

        if actual_presence != (expected_before, expected_after):
            raise ValueError(
                f"{self.change_type.value} section requires "
                f"before={expected_before} and after={expected_after}"
            )

        return self


class ChangeNarrative(BaseModel):
    """Validated semantic description generated for one section change."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    summary: NonEmptyText
    semantic_label: NonEmptyText | None = None
    key_points: tuple[NonEmptyText, ...] = ()


class InterpretedSectionChange(BaseModel):
    """Model narrative joined to deterministic section identity."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    change_type: SectionChangeType
    previous_section_index: int | None = None
    current_section_index: int | None = None
    narrative: ChangeNarrative


class PageChangeInterpretation(BaseModel):
    """Semantic interpretations for one persisted changed page version."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    url: HttpUrl
    version_number: int = Field(gt=0)
    changes: tuple[InterpretedSectionChange, ...]
