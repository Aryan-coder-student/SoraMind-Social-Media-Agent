"""Normalization contract."""

from abc import ABC, abstractmethod

from app.modules.company_knowledge.models.page import PageDocument


class NormalizerBase(ABC):
    """Contract for webpage normalization."""

    @abstractmethod
    def normalize(self, page: PageDocument) -> PageDocument:
        """Normalize a webpage document."""
        ...
