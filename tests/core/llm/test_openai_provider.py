"""Tests for the OpenAI provider adapter."""

from types import SimpleNamespace
from typing import Any

import pytest

from app.core.llm.providers.openai import OpenAIProvider


class FakeCompletions:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        message = SimpleNamespace(content="OpenAI text")
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeOpenAIClient:
    def __init__(self) -> None:
        self.completions = FakeCompletions()
        self.chat = SimpleNamespace(completions=self.completions)


@pytest.mark.asyncio
async def test_generates_text_with_system_and_user_messages() -> None:
    client = FakeOpenAIClient()
    provider = OpenAIProvider(
        api_key="unused",
        model="configured-openai-model",
        client=client,
    )

    result = await provider.generate("User prompt", "System prompt")

    assert provider.model == "configured-openai-model"
    assert result == "OpenAI text"
    assert client.completions.calls == [
        {
            "model": "configured-openai-model",
            "messages": [
                {"role": "system", "content": "System prompt"},
                {"role": "user", "content": "User prompt"},
            ],
        }
    ]


@pytest.mark.asyncio
async def test_generates_without_system_prompt() -> None:
    client = FakeOpenAIClient()
    provider = OpenAIProvider("unused", "configured-openai-model", client)

    await provider.generate("User prompt")

    assert client.completions.calls[0]["messages"] == [
        {"role": "user", "content": "User prompt"}
    ]
