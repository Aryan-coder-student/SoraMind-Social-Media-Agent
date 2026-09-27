"""Text-cleaning adapters for normalization."""

from abc import ABC, abstractmethod

from unicode_sanity import sanitize


class TextCleaner(ABC):
    """Application-facing contract for Unicode text cleaning."""

    @abstractmethod
    def clean(self, text: str) -> str:
        """Clean Unicode noise without exposing the third-party library."""
        ...


class UnicodeSanityAdapter(TextCleaner):
    """Adapter around the unicode-sanity package."""

    def clean(self, text: str) -> str:
        """Remove invisible and bidi control characters from text."""
        return sanitize(text, policy="strict").text
