"""Tests for provider registration and creation."""

import pytest

from app.core.llm.base import LLMProvider
from app.core.llm.registry import LLMRegistry, create_default_registry
from app.core.llm.spec import ProviderSpec


class FakeProvider(LLMProvider):
    """Provider fake used to inspect registry construction."""

    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> str:
        return prompt


def fake_spec() -> ProviderSpec:
    return ProviderSpec(
        name="fake",
        provider_factory=FakeProvider,
        default_model="fake-default",
        api_key_env="FAKE_API_KEY",
    )


def test_registers_and_retrieves_provider_spec() -> None:
    registry = LLMRegistry()
    spec = fake_spec()

    registry.register(spec)

    assert registry.get("fake") is spec
    assert registry.registered_names == ("fake",)


def test_creates_provider_with_default_model() -> None:
    registry = LLMRegistry()
    registry.register(fake_spec())

    provider = registry.create("fake", api_key="secret")

    assert isinstance(provider, FakeProvider)
    assert provider.api_key == "secret"
    assert provider.model == "fake-default"


def test_creates_provider_with_configured_model() -> None:
    registry = LLMRegistry()
    registry.register(fake_spec())

    provider = registry.create(
        "fake",
        api_key="secret",
        model="configured-model",
    )

    assert provider.model == "configured-model"


def test_duplicate_provider_name_raises_clear_error() -> None:
    registry = LLMRegistry()
    registry.register(fake_spec())

    with pytest.raises(ValueError, match="already registered: fake"):
        registry.register(fake_spec())


def test_unknown_provider_name_raises_clear_error() -> None:
    registry = LLMRegistry()

    with pytest.raises(KeyError, match="Unknown LLM provider: missing"):
        registry.create("missing", api_key="unused")


def test_default_registry_contains_all_builtin_providers() -> None:
    registry = create_default_registry()

    assert registry.registered_names == ("openai", "anthropic", "groq")
    assert registry.get("openai").api_key_env == "OPENAI_API_KEY"
    assert registry.get("anthropic").api_key_env == "ANTHROPIC_API_KEY"
    assert registry.get("groq").api_key_env == "GROQ_API_KEY"
