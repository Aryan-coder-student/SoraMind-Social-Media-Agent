"""Tests for provider-independent LLM section-change summaries."""

import json

import pytest

from app.core.llm.base import LLMProvider
from app.modules.company_knowledge.errors import InvalidChangeSummaryError
from app.modules.company_knowledge.extraction.change_summary import (
    LLMSectionChangeSummarizer,
)
from app.modules.company_knowledge.models.change_summary import (
    ChangeSummary,
    SectionChangeContext,
    SectionChangeType,
)
from app.modules.company_knowledge.models.page import Heading
from app.modules.company_knowledge.models.version import SectionVersion


class RecordingProvider(LLMProvider):
    """Return configured text while recording provider-independent requests."""

    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list[tuple[str, str | None]] = []

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> str:
        self.calls.append((prompt, system_prompt))
        return self.response


def make_section(index: int, text: str) -> SectionVersion:
    return SectionVersion(
        index=index,
        headings=[Heading(level=2, text="Pricing")],
        text=text,
        fingerprint=str(index) * 64,
    )


@pytest.mark.parametrize(
    ("change_type", "before", "after"),
    [
        (SectionChangeType.ADDED, None, None),
        (
            SectionChangeType.ADDED,
            make_section(1, "Before"),
            make_section(2, "After"),
        ),
        (SectionChangeType.REMOVED, None, None),
        (
            SectionChangeType.REMOVED,
            make_section(1, "Before"),
            make_section(2, "After"),
        ),
        (
            SectionChangeType.CHANGED,
            make_section(1, "Before"),
            None,
        ),
        (
            SectionChangeType.CHANGED,
            None,
            make_section(2, "After"),
        ),
    ],
)
def test_rejects_section_context_with_invalid_version_presence(
    change_type: SectionChangeType,
    before: SectionVersion | None,
    after: SectionVersion | None,
) -> None:
    with pytest.raises(ValueError, match=f"{change_type.value} change requires"):
        SectionChangeContext(
            change_type=change_type,
            before=before,
            after=after,
        )


@pytest.mark.asyncio
async def test_changed_section_returns_validated_summary() -> None:
    provider = RecordingProvider(
        json.dumps(
            {
                "summary": "Pricing now includes a Pro plan.",
                "category": "pricing",
                "key_points": ["A Pro plan was added."],
            }
        )
    )
    summarizer = LLMSectionChangeSummarizer(provider)
    change = SectionChangeContext(
        change_type=SectionChangeType.CHANGED,
        before=make_section(1, "Starter plan"),
        after=make_section(2, "Starter and Pro plans"),
    )

    summary = await summarizer.summarize(change)

    assert summarizer.prompt_version == "section-change-summary-v1"
    assert summary == ChangeSummary(
        summary="Pricing now includes a Pro plan.",
        category="pricing",
        key_points=("A Pro plan was added.",),
    )
    prompt, system_prompt = provider.calls[0]
    assert "Starter plan" in prompt
    assert "Starter and Pro plans" in prompt
    assert system_prompt is not None
    assert "Use only the supplied facts" in system_prompt


@pytest.mark.asyncio
async def test_added_section_prompt_contains_only_current_content() -> None:
    provider = RecordingProvider(
        '{"summary":"Careers were added.","category":"careers",'
        '"key_points":[]}'
    )
    summarizer = LLMSectionChangeSummarizer(provider)
    change = SectionChangeContext(
        change_type=SectionChangeType.ADDED,
        after=make_section(4, "Explore open roles"),
    )

    await summarizer.summarize(change)

    prompt, _ = provider.calls[0]
    prompt_payload = json.loads(prompt)
    assert prompt_payload["change_type"] == "added"
    assert prompt_payload["before"] is None
    assert prompt_payload["after"]["text"] == "Explore open roles"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response",
    [
        "not JSON",
        '{"summary":" ","category":null,"key_points":[]}',
        '{"summary":"Removed.","category":" ","key_points":[]}',
        '{"summary":"Removed.","category":null,"key_points":[" "]}',
        (
            '{"summary":"Removed.","category":null,'
            '"key_points":[],"unsupported":true}'
        ),
    ],
)
async def test_invalid_provider_json_raises_change_context(
    response: str,
) -> None:
    summarizer = LLMSectionChangeSummarizer(RecordingProvider(response))
    change = SectionChangeContext(
        change_type=SectionChangeType.REMOVED,
        before=make_section(3, "Legacy plan"),
    )

    with pytest.raises(
        InvalidChangeSummaryError,
        match="removed section 3",
    ):
        await summarizer.summarize(change)
