"""SQLAlchemy schema for current normalized page and section state."""

from __future__ import annotations

from sqlalchemy import JSON, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for relational Phase 1 persistence tables."""


class PageRow(Base):
    """Current normalized state and fingerprint for one page."""

    __tablename__ = "pages"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        unique=True,
    )
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    canonical_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    fingerprint: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    sections: Mapped[list["SectionRow"]] = relationship(
        back_populates="page",
        cascade="all, delete-orphan",
        order_by="SectionRow.section_index",
        passive_deletes=True,
    )


class SectionRow(Base):
    """Current normalized state and fingerprint for one page section."""

    __tablename__ = "sections"
    __table_args__ = (
        UniqueConstraint(
            "page_id",
            "section_index",
            name="uq_sections_page_index",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    page_id: Mapped[int] = mapped_column(
        ForeignKey("pages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    section_index: Mapped[int] = mapped_column(Integer, nullable=False)
    dom_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    classes: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    headings: Mapped[list[dict[str, object]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    child_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    fingerprint: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    page: Mapped[PageRow] = relationship(back_populates="sections")
