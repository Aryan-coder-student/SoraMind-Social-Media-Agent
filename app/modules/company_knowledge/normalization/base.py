"""Base contract for page normalization."""

from abc import ABC, abstractmethod

from app.modules.company_knowledge.models.page import PageDocument


class NormalizerBase(ABC):
    """Contract for deterministic webpage normalization."""

    @abstractmethod
    def normalize(self, page: PageDocument) -> PageDocument:
        """Normalize a factual webpage document."""
        ...
