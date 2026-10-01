"""Contracts for optional semantic interpretation."""

from abc import ABC, abstractmethod

from app.modules.company_knowledge.models.change_interpretation import (
    ChangeNarrative,
    SectionChangeInput,
)


class ChangeInterpreter(ABC):
    """Interpret one deterministic section change semantically."""

    @abstractmethod
    async def interpret(
        self,
        change: SectionChangeInput,
    ) -> ChangeNarrative:
        """Return a validated semantic narrative for one change."""
        ...
