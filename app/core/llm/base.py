"""Provider-independent text generation contract."""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Generate plain text without exposing provider SDK responses."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> str:
        """Generate text from a user prompt and optional system prompt."""
        ...
