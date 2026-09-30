"""SQLAlchemy schema for stable page identity and lifecycle state."""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.schemas.base import Base


class PageRow(Base):
    """Stable page identity, lifecycle state, and current-version pointer."""

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
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    current_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("page_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    versions: Mapped[list["PageVersionRow"]] = relationship(
        back_populates="page",
        cascade="all, delete-orphan",
        order_by="PageVersionRow.version_number",
        passive_deletes=True,
        foreign_keys="PageVersionRow.page_id",
    )
