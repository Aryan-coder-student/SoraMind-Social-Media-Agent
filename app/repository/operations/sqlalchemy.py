"""SQLAlchemy persistence for current Company Knowledge and page history."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload, sessionmaker

from app.database.schemas.sqlalchemy import PageRow, PageVersionRow
from pydantic import HttpUrl

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
    section_to_row,
    section_to_version_row,
    string_to_url,
    url_to_string,
)


class SQLAlchemyRepository(Repository):
    """Persist current state and immutable history in one transaction."""

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
        """Persist a page and snapshot it only when its fingerprint changes."""
        self._validate_section_fingerprints(page, section_fingerprints)

        url = url_to_string(page.url)

        with self._session_factory() as session:
            with session.begin():
                row = session.scalar(
                    select(PageRow).where(PageRow.url == url)
                )

                if row is None:
                    row = PageRow(url=url, fingerprint=page_fingerprint)
                    session.add(row)
                    self._replace_current_state(
                        session,
                        row,
                        page,
                        page_fingerprint,
                        section_fingerprints,
                    )
                    row.versions.append(
                        self._create_version_row(
                            page,
                            page_fingerprint,
                            section_fingerprints,
                            version_number=1,
                        )
                    )
                    result = SavePageResult(
                        status=SavePageStatus.NEW,
                        version_number=1,
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

    def _update_existing_page(
        self,
        session: Session,
        row: PageRow,
        page: PageDocument,
        page_fingerprint: str,
        section_fingerprints: list[str],
    ) -> SavePageResult:
        """Update current state and append history when content changed."""
        content_changed = row.fingerprint != page_fingerprint
        was_active = row.is_active
        latest_version = self._latest_version_number(session, row.id)

        self._replace_current_state(
            session,
            row,
            page,
            page_fingerprint,
            section_fingerprints,
        )

        if not content_changed:
            status = (
                SavePageStatus.REACTIVATED
                if not was_active
                else SavePageStatus.UNCHANGED
            )
            return SavePageResult(
                status=status,
                version_number=latest_version,
            )

        next_version = latest_version + 1
        row.versions.append(
            self._create_version_row(
                page,
                page_fingerprint,
                section_fingerprints,
                version_number=next_version,
            )
        )
        return SavePageResult(
            status=SavePageStatus.CHANGED,
            version_number=next_version,
        )

    @staticmethod
    def _replace_current_state(
        session: Session,
        row: PageRow,
        page: PageDocument,
        page_fingerprint: str,
        section_fingerprints: list[str],
    ) -> None:
        """Replace current factual state without committing the transaction."""
        if row.sections:
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
        row.is_active = True
        row.sections = [
            section_to_row(section, fingerprint)
            for section, fingerprint in zip(
                page.sections,
                section_fingerprints,
                strict=True,
            )
        ]

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
            canonical_url=(
                url_to_string(page.canonical_url)
                if page.canonical_url is not None
                else None
            ),
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
    def _latest_version_number(session: Session, page_id: int) -> int:
        """Return the latest per-page version number."""
        latest = session.scalar(
            select(func.max(PageVersionRow.version_number)).where(
                PageVersionRow.page_id == page_id
            )
        )
        return int(latest or 0)

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
        """Return the newest immutable snapshot for a page."""
        validated_url = url_to_string(url)

        with self._session_factory() as session:
            row = session.scalar(
                self._version_query(validated_url)
                .order_by(PageVersionRow.version_number.desc())
                .limit(1)
            )
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
    def _version_query(validated_url: str):
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
