"""Repository mapping helpers between domain models and SQLAlchemy rows."""

from pydantic import HttpUrl, TypeAdapter

from app.database.schemas.sqlalchemy import PageRow, SectionRow
_HTTP_URL_ADAPTER = TypeAdapter(HttpUrl)


from app.modules.company_knowledge.models.page import (
    Heading,
    PageDocument,
    PageSection,
)


def url_to_string(url: HttpUrl | str) -> str:
    """Validate an HTTP(S) URL and return its persistence representation."""
    return str(_HTTP_URL_ADAPTER.validate_python(url))


def section_to_row(
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


def row_to_page_document(
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
