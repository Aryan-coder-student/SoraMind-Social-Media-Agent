"""Models used to summarize deterministic section changes."""

from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.modules.company_knowledge.models.version import SectionVersion


class SectionChangeType(str, Enum):
    """Kind of deterministic section change."""

    ADDED = "added"
    REMOVED = "removed"
    CHANGED = "changed"


@dataclass(frozen=True)
class SectionChangeContext:
    """Before/after section data for one deterministic change."""

    change_type: SectionChangeType
    before: SectionVersion | None = None
    after: SectionVersion | None = None

    @property
    def previous_section_index(self) -> int | None:
        """Return the previous index when a previous section exists."""
        return self.before.index if self.before is not None else None

    @property
    def current_section_index(self) -> int | None:
        """Return the current index when a current section exists."""
        return self.after.index if self.after is not None else None


class ChangeSummary(BaseModel):
    """Validated summary returned by the LLM for one section change."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    summary: str = Field(min_length=1)
    category: str | None = Field(default=None, min_length=1)
    key_points: tuple[str, ...] = ()


class SectionChangeSummary(BaseModel):
    """Summary joined with deterministic section identity."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    change_type: SectionChangeType
    previous_section_index: int | None = None
    current_section_index: int | None = None
    details: ChangeSummary


class PageChangeSummary(BaseModel):
    """LLM summaries for one persisted changed page version."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    url: HttpUrl
    version_number: int = Field(gt=0)
    changes: tuple[SectionChangeSummary, ...]
