"""Resolve configured LLM providers without provider-specific branching."""

from typing import Any

from app.core.llm.base import LLMProvider
from app.core.llm.providers.anthropic import AnthropicProvider
from app.core.llm.providers.groq import GroqProvider
from app.core.llm.providers.openai import OpenAIProvider
from app.core.llm.spec import ProviderSpec


class LLMRegistry:
    """Register provider specifications and construct provider instances."""

    def __init__(self) -> None:
        self._specs: dict[str, ProviderSpec] = {}

    @property
    def registered_names(self) -> tuple[str, ...]:
        """Return provider names in registration order."""
        return tuple(self._specs)

    def register(self, spec: ProviderSpec) -> None:
        """Register a provider specification under its unique name."""
        if spec.name in self._specs:
            raise ValueError(f"LLM provider already registered: {spec.name}")

        self._specs[spec.name] = spec

    def get(self, name: str) -> ProviderSpec:
        """Return a registered provider specification."""
        try:
            return self._specs[name]
        except KeyError as error:
            raise KeyError(f"Unknown LLM provider: {name}") from error

    def create(
        self,
        name: str,
        *,
        api_key: str,
        model: str | None = None,
        **provider_options: Any,
    ) -> LLMProvider:
        """Create a provider through its registered factory."""
        return self.get(name).create(
            api_key=api_key,
            model=model,
            **provider_options,
        )


def create_default_registry() -> LLMRegistry:
    """Create a registry containing the three Phase 1 providers."""
    registry = LLMRegistry()
    registry.register(
        ProviderSpec(
            name="openai",
            provider_factory=OpenAIProvider,
            default_model="gpt-5.6",
            api_key_env="OPENAI_API_KEY",
        )
    )
    registry.register(
        ProviderSpec(
            name="anthropic",
            provider_factory=AnthropicProvider,
            default_model="claude-sonnet-5",
            api_key_env="ANTHROPIC_API_KEY",
        )
    )
    registry.register(
        ProviderSpec(
            name="groq",
            provider_factory=GroqProvider,
            default_model="openai/gpt-oss-120b",
            api_key_env="GROQ_API_KEY",
        )
    )
    return registry
