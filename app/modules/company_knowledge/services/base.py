"""Shared result models for Company Knowledge services."""

from dataclasses import dataclass

from pydantic import HttpUrl

from app.modules.company_knowledge.models.page import PageDocument
from app.modules.company_knowledge.models.section_change import SectionChangeSet
from app.modules.company_knowledge.models.version import SavePageResult


@dataclass(frozen=True)
class ProcessedPage:
    """Normalized and persisted page ready for change analysis."""

    page: PageDocument
    save_result: SavePageResult
    section_fingerprints: tuple[str, ...]


@dataclass(frozen=True)
class PageBuildResult:
    """Final pipeline result for one processed page."""

    url: HttpUrl
    save_result: SavePageResult
    section_changes: SectionChangeSet | None = None
