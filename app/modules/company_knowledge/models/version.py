"""Domain models for immutable Company Knowledge page versions."""

from enum import Enum

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl

from app.modules.company_knowledge.models.page import Heading


class SavePageStatus(str, Enum):
    """Outcome of persisting one normalized page."""

    NEW = "new"
    UNCHANGED = "unchanged"
    CHANGED = "changed"
    REACTIVATED = "reactivated"


class SavePageResult(BaseModel):
    """Persistence outcome and resulting latest version number."""

    model_config = ConfigDict(frozen=True)

    status: SavePageStatus
    version_number: int = Field(gt=0)


class SectionVersion(BaseModel):
    """Immutable snapshot of one normalized page section."""

    model_config = ConfigDict(frozen=True)

    index: int
    headings: list[Heading] = Field(default_factory=list)
    text: str
    fingerprint: str


class PageVersion(BaseModel):
    """Immutable content snapshot created for a page fingerprint."""

    model_config = ConfigDict(frozen=True)

    version_number: int = Field(gt=0)
    url: HttpUrl
    title: str | None = None
    meta_description: str | None = None
    fingerprint: str
    captured_at: AwareDatetime
    sections: list[SectionVersion] = Field(default_factory=list)
