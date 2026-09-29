"""SQLAlchemy implementation of current Company Knowledge persistence."""

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.database.schemas.sqlalchemy import PageRow, SectionRow
from app.modules.company_knowledge.models.page import (
    Heading,
    PageDocument,
    PageSection,
)
from app.repository.base import Repository


class SQLAlchemyRepository(Repository):
    """Persist current page state through a SQLAlchemy session factory."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
    ) -> None:
        self._session_factory = session_factory

    def save_page(
        self,
        page: PageDocument,
        page_fingerprint: str,
        section_fingerprints: list[str],
    ) -> None:
        """Insert or replace the current state for one page URL."""
        if len(page.sections) != len(section_fingerprints):
            raise ValueError(
                "section fingerprint count must match page section count"
            )

        url = str(page.url)

        with self._session_factory() as session:
            row = session.scalar(
                select(PageRow).where(PageRow.url == url)
            )

            if row is None:
                row = PageRow(
                    url=url,
                    fingerprint=page_fingerprint,
                )
                session.add(row)
            else:
                row.sections.clear()
                session.flush()

            row.title = page.title
            row.meta_description = page.meta_description
            row.canonical_url = (
                str(page.canonical_url)
                if page.canonical_url is not None
                else None
            )
            row.fingerprint = page_fingerprint
            row.sections = [
                self._to_section_row(section, fingerprint)
                for section, fingerprint in zip(
                    page.sections,
                    section_fingerprints,
                    strict=True,
                )
            ]

            session.commit()

    def get_page(
        self,
        url: str,
    ) -> PageDocument | None:
        """Return the current normalized page for a URL."""
        with self._session_factory() as session:
            row = session.scalar(
                select(PageRow).where(PageRow.url == url)
            )

            if row is None:
                return None

            return self._to_page_document(row)

    def get_page_fingerprint(
        self,
        url: str,
    ) -> str | None:
        """Return the current page fingerprint for a URL."""
        with self._session_factory() as session:
            return session.scalar(
                select(PageRow.fingerprint).where(PageRow.url == url)
            )

    def delete_page(
        self,
        url: str,
    ) -> bool:
        """Delete the current page state and return whether it existed."""
        with self._session_factory() as session:
            row = session.scalar(
                select(PageRow).where(PageRow.url == url)
            )

            if row is None:
                return False

            session.delete(row)
            session.commit()
            return True

    @staticmethod
    def _to_section_row(
        section: PageSection,
        fingerprint: str,
    ) -> SectionRow:
        """Convert a domain page section into a relational row."""
        return SectionRow(
            section_index=section.index,
            dom_id=section.id,
            classes=list(section.classes),
            headings=[
                {
                    "level": heading.level,
                    "text": heading.text,
                }
                for heading in section.headings
            ],
            text=section.text,
            child_count=section.child_count,
            fingerprint=fingerprint,
        )

    @staticmethod
    def _to_page_document(
        row: PageRow,
    ) -> PageDocument:
        """Convert relational rows back into the factual domain model."""
        return PageDocument(
            url=row.url,
            title=row.title,
            meta_description=row.meta_description,
            canonical_url=row.canonical_url,
            sections=[
                PageSection(
                    index=section.section_index,
                    id=section.dom_id,
                    classes=list(section.classes),
                    headings=[
                        Heading(
                            level=int(heading["level"]),
                            text=str(heading["text"]),
                        )
                        for heading in section.headings
                    ],
                    text=section.text,
                    child_count=section.child_count,
                )
                for section in row.sections
            ],
        )
