"""Compatibility exports for split SQLAlchemy schema modules."""

from app.database.schemas.base import Base
from app.database.schemas.page import PageRow
from app.database.schemas.version import PageVersionRow, SectionVersionRow

__all__ = [
    "Base",
    "PageRow",
    "PageVersionRow",
    "SectionVersionRow",
]
