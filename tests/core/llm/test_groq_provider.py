"""Tests for the Groq provider adapter."""

from types import SimpleNamespace
from typing import Any

import pytest

from app.core.llm.providers.groq import GroqProvider


class FakeCompletions:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        message = SimpleNamespace(content="Groq text")
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeGroqClient:
    def __init__(self) -> None:
        self.completions = FakeCompletions()
        self.chat = SimpleNamespace(completions=self.completions)


@pytest.mark.asyncio
async def test_generates_text_with_system_and_user_messages() -> None:
    client = FakeGroqClient()
    provider = GroqProvider(
        api_key="unused",
        model="configured-groq-model",
        client=client,
    )

    result = await provider.generate("User prompt", "System prompt")

    assert provider.model == "configured-groq-model"
    assert result == "Groq text"
    assert client.completions.calls == [
        {
            "model": "configured-groq-model",
            "messages": [
                {"role": "system", "content": "System prompt"},
                {"role": "user", "content": "User prompt"},
            ],
        }
    ]


@pytest.mark.asyncio
async def test_generates_without_system_prompt() -> None:
    client = FakeGroqClient()
    provider = GroqProvider("unused", "configured-groq-model", client)

    await provider.generate("User prompt")

    assert client.completions.calls[0]["messages"] == [
        {"role": "user", "content": "User prompt"}
    ]
