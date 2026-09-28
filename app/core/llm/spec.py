"""Provider-agnostic registration metadata."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.core.llm.base import LLMProvider

ProviderFactory = Callable[..., LLMProvider]


@dataclass(frozen=True)
class ProviderSpec:
    """Describe how to identify and construct one LLM provider."""

    name: str
    provider_factory: ProviderFactory
    default_model: str
    api_key_env: str

    def create(
        self,
        *,
        api_key: str,
        model: str | None = None,
        **provider_options: Any,
    ) -> LLMProvider:
        """Construct the provider with an optional model override."""
        return self.provider_factory(
            api_key=api_key,
            model=model or self.default_model,
            **provider_options,
        )
