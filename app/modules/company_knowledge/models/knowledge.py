"""Pydantic models for semantic company knowledge extracted from webpage sections."""

from pydantic import BaseModel, Field, HttpUrl


class SectionKnowledge(BaseModel):
    """Semantic understanding extracted from one page section."""

    section_index: int
    semantic_label: str | None = None
    summary: str
    key_points: list[str] = Field(default_factory=list)


class PageKnowledge(BaseModel):
    """Semantic company knowledge extracted from one webpage."""

    url: HttpUrl
    summary: str
    sections: list[SectionKnowledge] = Field(default_factory=list)
