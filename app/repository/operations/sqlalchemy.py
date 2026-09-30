"""SQLAlchemy persistence for page identity and immutable Company Knowledge versions."""

from pydantic import HttpUrl
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload, sessionmaker
from sqlalchemy.sql import Select

from app.database.schemas.page import PageRow
from app.database.schemas.version import PageVersionRow
from app.modules.company_knowledge.models.page import PageDocument
from app.modules.company_knowledge.models.version import (
    PageVersion,
    SavePageResult,
    SavePageStatus,
)
from app.repository.base import Repository
from app.repository.operations.utils import (
    row_to_page_document,
    row_to_page_version,
    section_to_version_row,
    string_to_url,
    url_to_string,
)


class SQLAlchemyRepository(Repository):
    """Persist stable page identities pointing at immutable content versions."""

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
    ) -> SavePageResult:
        """Create a version only when the page fingerprint changes."""
        self._validate_section_fingerprints(page, section_fingerprints)
        url = url_to_string(page.url)

        with self._session_factory() as session:
            with session.begin():
                row = session.scalar(
                    select(PageRow).where(PageRow.url == url)
                )

                if row is None:
                    result = self._insert_new_page(
                        session,
                        url,
                        page,
                        page_fingerprint,
                        section_fingerprints,
                    )
                else:
                    result = self._update_existing_page(
                        session,
                        row,
                        page,
                        page_fingerprint,
                        section_fingerprints,
                    )

            return result

    def _insert_new_page(
        self,
        session: Session,
        url: str,
        page: PageDocument,
        page_fingerprint: str,
        section_fingerprints: list[str],
    ) -> SavePageResult:
        """Insert stable page identity and immutable version one."""
        row = PageRow(url=url)
        session.add(row)
        session.flush()

        version = self._create_version_row(
            page,
            page_fingerprint,
            section_fingerprints,
            version_number=1,
        )
        row.versions.append(version)
        session.flush()
        row.current_version_id = version.id

        return SavePageResult(
            status=SavePageStatus.NEW,
            version_number=1,
        )

    def _update_existing_page(
        self,
        session: Session,
        row: PageRow,
        page: PageDocument,
        page_fingerprint: str,
        section_fingerprints: list[str],
    ) -> SavePageResult:
        """Reactivate or advance the page's immutable current-version pointer."""
        current_version = self._get_current_version(session, row)
        was_active = row.is_active
        row.is_active = True

        if current_version.fingerprint == page_fingerprint:
            status = (
                SavePageStatus.REACTIVATED
                if not was_active
                else SavePageStatus.UNCHANGED
            )
            return SavePageResult(
                status=status,
                version_number=current_version.version_number,
            )

        next_version = current_version.version_number + 1
        version = self._create_version_row(
            page,
            page_fingerprint,
            section_fingerprints,
            version_number=next_version,
        )
        row.versions.append(version)
        session.flush()
        row.current_version_id = version.id

        return SavePageResult(
            status=SavePageStatus.CHANGED,
            version_number=next_version,
        )

    @staticmethod
    def _get_current_version(
        session: Session,
        row: PageRow,
    ) -> PageVersionRow:
        """Load the immutable version currently selected by a page identity."""
        if row.current_version_id is None:
            raise RuntimeError(
                f"page {row.url!r} has no current version"
            )

        version = session.get(PageVersionRow, row.current_version_id)
        if version is None:
            raise RuntimeError(
                f"page {row.url!r} points to a missing current version"
            )
        if version.page_id != row.id:
            raise RuntimeError(
                f"current version {version.id} does not belong to page {row.id}"
            )
        return version

    @staticmethod
    def _create_version_row(
        page: PageDocument,
        page_fingerprint: str,
        section_fingerprints: list[str],
        version_number: int,
    ) -> PageVersionRow:
        """Build one complete immutable page snapshot."""
        return PageVersionRow(
            version_number=version_number,
            title=page.title,
            meta_description=page.meta_description,
            fingerprint=page_fingerprint,
            sections=[
                section_to_version_row(section, fingerprint)
                for section, fingerprint in zip(
                    page.sections,
                    section_fingerprints,
                    strict=True,
                )
            ],
        )

    @staticmethod
    def _validate_section_fingerprints(
        page: PageDocument,
        section_fingerprints: list[str],
    ) -> None:
        if len(page.sections) != len(section_fingerprints):
            raise ValueError(
                "section fingerprint count must match page section count"
            )

    def get_page(
        self,
        url: HttpUrl,
    ) -> PageDocument | None:
        """Return the persisted content subset for the current version."""
        validated_url = url_to_string(url)

        with self._session_factory() as session:
            row = session.scalar(self._current_version_query(validated_url))
            return row_to_page_document(row) if row is not None else None

    def get_page_fingerprint(
        self,
        url: HttpUrl,
    ) -> str | None:
        """Return the fingerprint of the page's current version."""
        validated_url = url_to_string(url)

        with self._session_factory() as session:
            return session.scalar(
                select(PageVersionRow.fingerprint)
                .join(
                    PageRow,
                    (PageRow.current_version_id == PageVersionRow.id)
                    & (PageVersionRow.page_id == PageRow.id),
                )
                .where(PageRow.url == validated_url)
            )

    def delete_page(
        self,
        url: HttpUrl,
    ) -> bool:
        """Delete a page identity and all historical versions."""
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

    def get_page_versions(self, url: HttpUrl) -> list[PageVersion]:
        """Return immutable snapshots in ascending version order."""
        validated_url = url_to_string(url)

        with self._session_factory() as session:
            rows = session.scalars(
                self._version_query(validated_url).order_by(
                    PageVersionRow.version_number
                )
            ).all()
            return [row_to_page_version(row) for row in rows]

    def get_page_version(
        self,
        url: HttpUrl,
        version_number: int,
    ) -> PageVersion | None:
        """Return one exact historical snapshot."""
        validated_url = url_to_string(url)

        with self._session_factory() as session:
            row = session.scalar(
                self._version_query(validated_url).where(
                    PageVersionRow.version_number == version_number
                )
            )
            return row_to_page_version(row) if row is not None else None

    def get_latest_version(self, url: HttpUrl) -> PageVersion | None:
        """Return the current immutable snapshot for a page."""
        validated_url = url_to_string(url)

        with self._session_factory() as session:
            row = session.scalar(self._current_version_query(validated_url))
            return row_to_page_version(row) if row is not None else None

    def mark_missing_pages_inactive(
        self,
        seen_urls: set[HttpUrl],
    ) -> list[HttpUrl]:
        """Deactivate active pages absent from one completed crawl."""
        persisted_seen_urls = {url_to_string(url) for url in seen_urls}

        with self._session_factory() as session:
            with session.begin():
                query = select(PageRow).where(PageRow.is_active.is_(True))
                if persisted_seen_urls:
                    query = query.where(PageRow.url.not_in(persisted_seen_urls))

                missing_rows = list(
                    session.scalars(query.order_by(PageRow.url)).all()
                )
                for row in missing_rows:
                    row.is_active = False

                return [string_to_url(row.url) for row in missing_rows]

    @staticmethod
    def _current_version_query(
        validated_url: str,
    ) -> Select[tuple[PageVersionRow]]:
        """Build the eager-loaded query for a page's selected current version."""
        return (
            select(PageVersionRow)
            .join(
                PageRow,
                (PageRow.current_version_id == PageVersionRow.id)
                & (PageVersionRow.page_id == PageRow.id),
            )
            .options(
                selectinload(PageVersionRow.page),
                selectinload(PageVersionRow.sections),
            )
            .where(PageRow.url == validated_url)
        )

    @staticmethod
    def _version_query(
        validated_url: str,
    ) -> Select[tuple[PageVersionRow]]:
        """Build the eager-loaded query shared by history reads."""
        return (
            select(PageVersionRow)
            .join(PageVersionRow.page)
            .options(
                selectinload(PageVersionRow.page),
                selectinload(PageVersionRow.sections),
            )
            .where(PageRow.url == validated_url)
        )
