"""Resolve deterministic section changes for persisted pages."""

from app.modules.company_knowledge.models.section_change import SectionChangeSet
from app.modules.company_knowledge.models.version import (
    SavePageStatus,
    SectionVersion,
)
from app.modules.company_knowledge.section_changes import classify_section_changes
from app.modules.company_knowledge.services.base import ProcessedPage
from app.repository.base import Repository


class CompanyKnowledgeChangeService:
    """Compare a changed page with its immediately previous persisted version."""

    def __init__(self, repository: Repository) -> None:
        self.repository = repository

    def get_changes(
        self,
        processed_page: ProcessedPage,
    ) -> SectionChangeSet | None:
        """Return section changes only when persistence created a new version."""
        save_result = processed_page.save_result

        if save_result.status != SavePageStatus.CHANGED:
            return None

        previous_version = self.repository.get_page_version(
            processed_page.page.url,
            save_result.version_number - 1,
        )
        if previous_version is None:
            raise RuntimeError(
                "previous version missing for changed page "
                f"{processed_page.page.url}"
            )

        current_sections = [
            SectionVersion(
                index=section.index,
                headings=section.headings,
                text=section.text,
                fingerprint=fingerprint,
            )
            for section, fingerprint in zip(
                processed_page.page.sections,
                processed_page.section_fingerprints,
                strict=True,
            )
        ]

        section_changes = classify_section_changes(
            previous_version.sections,
            current_sections,
        )
        return section_changes
