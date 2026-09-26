"""Pydantic models for factual webpage structure extracted from the DOM."""

from pydantic import BaseModel, Field, HttpUrl


class Heading(BaseModel):
    """A heading found inside a page section."""

    level: int
    text: str


class PageSection(BaseModel):
    """A structural section extracted from a rendered webpage."""

    index: int
    id: str | None = None
    classes: list[str] = Field(default_factory=list)
    headings: list[Heading] = Field(default_factory=list)
    text: str
    child_count: int = 0


class PageDocument(BaseModel):
    """Factual representation of one rendered webpage."""

    url: HttpUrl
    title: str | None = None
    meta_description: str | None = None
    canonical_url: HttpUrl | None = None
    sections: list[PageSection] = Field(default_factory=list)
