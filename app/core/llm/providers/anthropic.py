"""Anthropic text generation adapter."""

from typing import Any

from anthropic import AsyncAnthropic

from app.core.llm.base import LLMProvider


class AnthropicProvider(LLMProvider):
    """Generate plain text through Anthropic messages."""

    def __init__(
        self,
        api_key: str,
        model: str,
        max_tokens: int = 1_024,
        client: Any | None = None,
    ) -> None:
        self.model = model
        self.max_tokens = max_tokens
        self.client = (
            client if client is not None else AsyncAnthropic(api_key=api_key)
        )

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> str:
        """Return generated text from Anthropic text blocks."""
        request: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }

        if system_prompt is not None:
            request["system"] = system_prompt

        response = await self.client.messages.create(**request)
        return "".join(
            block.text
            for block in response.content
            if getattr(block, "type", None) == "text"
        )
