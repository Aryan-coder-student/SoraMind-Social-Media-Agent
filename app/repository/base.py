"""Repository contract for current Company Knowledge persistence."""

from abc import ABC, abstractmethod

from app.modules.company_knowledge.models.page import PageDocument


class Repository(ABC):
    """Persist and retrieve the current normalized Company Knowledge state."""

    @abstractmethod
    def save_page(
        self,
        page: PageDocument,
        page_fingerprint: str,
        section_fingerprints: list[str],
    ) -> None:
        """Insert or replace the current state for one page URL."""
        ...

    @abstractmethod
    def get_page(
        self,
        url: str,
    ) -> PageDocument | None:
        """Return the current normalized page for a URL."""
        ...

    @abstractmethod
    def get_page_fingerprint(
        self,
        url: str,
    ) -> str | None:
        """Return the current page fingerprint for a URL."""
        ...

    @abstractmethod
    def delete_page(
        self,
        url: str,
    ) -> bool:
        """Delete the current page state and return whether it existed."""
        ...
