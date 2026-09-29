"""Groq text generation adapter."""

from typing import Any

from groq import AsyncGroq

from app.core.llm.base import LLMProvider


class GroqProvider(LLMProvider):
    """Generate plain text through Groq chat completions."""

    def __init__(
        self,
        api_key: str,
        model: str,
        client: Any | None = None,
    ) -> None:
        self.model = model
        self.client = client if client is not None else AsyncGroq(api_key=api_key)

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> str:
        """Return generated text from Groq."""
        messages = []

        if system_prompt is not None:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
        )
        return response.choices[0].message.content or ""
