"""LLM-backed summaries of deterministic section changes."""

import json

from pydantic import ValidationError

from app.core.llm.base import LLMProvider
from app.modules.company_knowledge.error import InvalidChangeSummaryError
from app.modules.company_knowledge.extraction.base import SectionChangeSummarizer
from app.modules.company_knowledge.extraction.prompts import (
    CHANGE_SUMMARY_PROMPT_VERSION,
    CHANGE_SUMMARY_SYSTEM_PROMPT,
)
from app.modules.company_knowledge.models.change_summary import (
    ChangeSummary,
    SectionChangeContext,
)
from app.modules.company_knowledge.models.version import SectionVersion


class LLMSectionChangeSummarizer(SectionChangeSummarizer):
    """Summarize section changes through an injected LLM provider."""

    prompt_version = CHANGE_SUMMARY_PROMPT_VERSION

    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    async def summarize(
        self,
        change: SectionChangeContext,
    ) -> ChangeSummary:
        """Generate and validate one section-change summary."""
        prompt = self._build_prompt(change)
        response = await self.provider.generate(
            prompt,
            system_prompt=CHANGE_SUMMARY_SYSTEM_PROMPT,
        )

        try:
            return ChangeSummary.model_validate_json(response)
        except ValidationError as error:
            raise InvalidChangeSummaryError(change, error) from error

    @classmethod
    def _build_prompt(cls, change: SectionChangeContext) -> str:
        """Serialize only factual before/after section content."""
        payload = {
            "change_type": change.change_type.value,
            "before": cls._section_payload(change.before),
            "after": cls._section_payload(change.after),
        }
        prompt = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return prompt

    @staticmethod
    def _section_payload(
        section: SectionVersion | None,
    ) -> dict[str, object] | None:
        """Return only section content needed by the LLM."""
        if section is None:
            return None

        section_payload = section.model_dump(
            include={"headings", "text"},
        )
        return section_payload
