"""SQLAlchemy implementation of current Company Knowledge persistence."""

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.database.schemas.sqlalchemy import PageRow
from pydantic import HttpUrl

from app.modules.company_knowledge.models.page import PageDocument
from app.repository.base import Repository
from app.repository.operations.utils import (
    row_to_page_document,
    section_to_row,
    url_to_string,
)


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

        url = url_to_string(page.url)

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
                url_to_string(page.canonical_url)
                if page.canonical_url is not None
                else None
            )
            row.fingerprint = page_fingerprint
            row.sections = [
                section_to_row(section, fingerprint)
                for section, fingerprint in zip(
                    page.sections,
                    section_fingerprints,
                    strict=True,
                )
            ]

            session.commit()

    def get_page(
        self,
        url: HttpUrl,
    ) -> PageDocument | None:
        """Return the current normalized page for a URL."""
        validated_url = url_to_string(url)

        with self._session_factory() as session:
            row = session.scalar(
                select(PageRow).where(PageRow.url == validated_url)
            )

            if row is None:
                return None

            return row_to_page_document(row)

    def get_page_fingerprint(
        self,
        url: HttpUrl,
    ) -> str | None:
        """Return the current page fingerprint for a URL."""
        validated_url = url_to_string(url)

        with self._session_factory() as session:
            return session.scalar(
                select(PageRow.fingerprint).where(PageRow.url == validated_url)
            )

    def delete_page(
        self,
        url: HttpUrl,
    ) -> bool:
        """Delete the current page state and return whether it existed."""
        validated_url = url_to_string(url)

        with self._session_factory() as session:
            row = session.scalar(
                select(PageRow).where(PageRow.url == validated_url)
            )

            if row is None:
                return False

            session.delete(row)
            session.commit()
            return True
