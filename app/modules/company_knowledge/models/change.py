"""Domain models for deterministic Company Knowledge section changes."""

from pydantic import BaseModel, ConfigDict

from app.modules.company_knowledge.models.version import SectionVersion


class SectionChange(BaseModel):
    """One persisted section that changed between page versions."""

    model_config = ConfigDict(frozen=True)

    before: SectionVersion
    after: SectionVersion


class SectionChangeSet(BaseModel):
    """Added, removed, and changed sections between two page versions."""

    model_config = ConfigDict(frozen=True)

    added: tuple[SectionVersion, ...] = ()
    removed: tuple[SectionVersion, ...] = ()
    changed: tuple[SectionChange, ...] = ()
