"""Repository contract for current Company Knowledge persistence."""

from abc import ABC, abstractmethod

from pydantic import HttpUrl

from app.modules.company_knowledge.models.page import PageDocument
from app.modules.company_knowledge.models.version import PageVersion, SavePageResult


class Repository(ABC):
    """Persist and retrieve the current normalized Company Knowledge state."""

    @abstractmethod
    def save_page(
        self,
        page: PageDocument,
        page_fingerprint: str,
        section_fingerprints: list[str],
    ) -> SavePageResult:
        """Persist current state and create history when content changes."""
        ...

    @abstractmethod
    def get_page(
        self,
        url: HttpUrl,
    ) -> PageDocument | None:
        """Return the current normalized page for a URL."""
        ...

    @abstractmethod
    def get_page_fingerprint(
        self,
        url: HttpUrl,
    ) -> str | None:
        """Return the current page fingerprint for a URL."""
        ...

    @abstractmethod
    def delete_page(
        self,
        url: HttpUrl,
    ) -> bool:
        """Delete the current page state and return whether it existed."""
        ...

    @abstractmethod
    def get_page_versions(self, url: HttpUrl) -> list[PageVersion]:
        """Return immutable snapshots in ascending version order."""
        ...

    @abstractmethod
    def get_page_version(
        self,
        url: HttpUrl,
        version_number: int,
    ) -> PageVersion | None:
        """Return one historical snapshot for a page URL."""
        ...

    @abstractmethod
    def get_latest_version(self, url: HttpUrl) -> PageVersion | None:
        """Return the latest historical snapshot for a page URL."""
        ...

    @abstractmethod
    def mark_missing_pages_inactive(
        self,
        seen_urls: set[HttpUrl],
    ) -> list[HttpUrl]:
        """Deactivate active pages absent from a completed crawl."""
        ...
