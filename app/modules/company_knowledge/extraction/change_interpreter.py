"""LLM-backed interpretation of deterministic section changes."""

import json
from typing import Any

from pydantic import ValidationError

from app.core.llm.base import LLMProvider
from app.modules.company_knowledge.extraction.base import ChangeInterpreter
from app.modules.company_knowledge.models.change_interpretation import (
    ChangeNarrative,
    SectionChangeInput,
)
from app.modules.company_knowledge.models.version import SectionVersion


SYSTEM_PROMPT = """You interpret factual website content changes.
Use only the supplied facts. Do not infer causes, intentions, or business impact.
Return exactly one JSON object with this schema:
{
  "summary": "non-empty factual summary",
  "semantic_label": "short label or null",
  "key_points": ["factual point"]
}
Do not include Markdown or additional keys.
"""
PROMPT_VERSION = "change-interpretation-v1"


class InvalidChangeNarrativeError(ValueError):
    """Raised when an LLM response is not a valid change narrative."""

    def __init__(
        self,
        change: SectionChangeInput,
        validation_error: ValidationError,
    ) -> None:
        section_index = (
            change.current_section_index
            if change.current_section_index is not None
            else change.previous_section_index
        )
        super().__init__(
            f"invalid LLM interpretation for "
            f"{change.change_type.value} section {section_index}: "
            f"{validation_error}"
        )


class LLMChangeInterpreter(ChangeInterpreter):
    """Generate and validate one narrative through an injected LLM provider."""

    prompt_version = PROMPT_VERSION

    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    async def interpret(
        self,
        change: SectionChangeInput,
    ) -> ChangeNarrative:
        """Interpret one deterministic change as a structured narrative."""
        response = await self.provider.generate(
            self._build_prompt(change),
            system_prompt=SYSTEM_PROMPT,
        )

        try:
            return ChangeNarrative.model_validate_json(response)
        except ValidationError as error:
            raise InvalidChangeNarrativeError(change, error) from error

    @classmethod
    def _build_prompt(cls, change: SectionChangeInput) -> str:
        """Serialize only factual before/after section content."""
        payload = {
            "change_type": change.change_type.value,
            "before": cls._section_payload(change.before),
            "after": cls._section_payload(change.after),
        }
        return json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        )

    @staticmethod
    def _section_payload(
        section: SectionVersion | None,
    ) -> dict[str, Any] | None:
        """Return the semantic section fields safe to send to an LLM."""
        if section is None:
            return None

        return {
            "headings": [
                {
                    "level": heading.level,
                    "text": heading.text,
                }
                for heading in section.headings
            ],
            "text": section.text,
        }
