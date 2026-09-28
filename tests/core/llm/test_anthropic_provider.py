"""Tests for the Anthropic provider adapter."""

from types import SimpleNamespace
from typing import Any

import pytest

from app.core.llm.providers.anthropic import AnthropicProvider


class FakeMessages:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        return SimpleNamespace(
            content=[
                SimpleNamespace(type="thinking", thinking="internal"),
                SimpleNamespace(type="text", text="Anthropic text"),
            ]
        )


class FakeAnthropicClient:
    def __init__(self) -> None:
        self.messages = FakeMessages()


@pytest.mark.asyncio
async def test_generates_text_with_anthropic_system_field() -> None:
    client = FakeAnthropicClient()
    provider = AnthropicProvider(
        api_key="unused",
        model="configured-anthropic-model",
        max_tokens=512,
        client=client,
    )

    result = await provider.generate("User prompt", "System prompt")

    assert provider.model == "configured-anthropic-model"
    assert result == "Anthropic text"
    assert client.messages.calls == [
        {
            "model": "configured-anthropic-model",
            "max_tokens": 512,
            "system": "System prompt",
            "messages": [{"role": "user", "content": "User prompt"}],
        }
    ]


@pytest.mark.asyncio
async def test_generates_without_system_prompt() -> None:
    client = FakeAnthropicClient()
    provider = AnthropicProvider("unused", "configured-anthropic-model", client=client)

    await provider.generate("User prompt")

    assert "system" not in client.messages.calls[0]
    assert client.messages.calls[0]["messages"] == [
        {"role": "user", "content": "User prompt"}
    ]
