"""Mapping helpers between Company Knowledge models and version rows."""

from datetime import UTC

from pydantic import HttpUrl, TypeAdapter

from app.database.schemas.version import PageVersionRow, SectionVersionRow
from app.modules.company_knowledge.models.page import (
    Heading,
    PageDocument,
    PageSection,
)
from app.modules.company_knowledge.models.version import PageVersion, SectionVersion

_HTTP_URL_ADAPTER = TypeAdapter(HttpUrl)


def url_to_string(url: HttpUrl | str) -> str:
    """Validate an HTTP(S) URL and return its persistence representation."""
    return str(_HTTP_URL_ADAPTER.validate_python(url))


def string_to_url(url: str) -> HttpUrl:
    """Convert a persisted URL into its validated domain representation."""
    return _HTTP_URL_ADAPTER.validate_python(url)


def section_to_version_row(
    section: PageSection,
    fingerprint: str,
) -> SectionVersionRow:
    """Convert a normalized section into an immutable snapshot row."""
    return SectionVersionRow(
        section_index=section.index,
        headings=[
            {"level": heading.level, "text": heading.text}
            for heading in section.headings
        ],
        text=section.text,
        fingerprint=fingerprint,
    )


def row_to_page_document(
    row: PageVersionRow,
) -> PageDocument:
    """Convert the current immutable version row into a PageDocument."""
    return PageDocument(
        url=row.page.url,
        title=row.title,
        meta_description=row.meta_description,
        sections=[
            PageSection(
                index=section.section_index,
                headings=[
                    Heading(
                        level=int(heading["level"]),
                        text=str(heading["text"]),
                    )
                    for heading in section.headings
                ],
                text=section.text,
            )
            for section in row.sections
        ],
    )


def row_to_page_version(row: PageVersionRow) -> PageVersion:
    """Convert an immutable relational snapshot into a domain model."""
    captured_at = row.captured_at
    if captured_at.tzinfo is None:
        captured_at = captured_at.replace(tzinfo=UTC)

    return PageVersion(
        version_number=row.version_number,
        url=row.page.url,
        title=row.title,
        meta_description=row.meta_description,
        fingerprint=row.fingerprint,
        captured_at=captured_at,
        sections=[
            SectionVersion(
                index=section.section_index,
                headings=[
                    Heading(
                        level=int(heading["level"]),
                        text=str(heading["text"]),
                    )
                    for heading in section.headings
                ],
                text=section.text,
                fingerprint=section.fingerprint,
            )
            for section in row.sections
        ],
    )
