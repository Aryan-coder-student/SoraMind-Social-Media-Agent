"""Tests for provider-independent LLM change interpretation."""

import json

import pytest

from app.core.llm.base import LLMProvider
from app.modules.company_knowledge.extraction.change_interpreter import (
    InvalidChangeNarrativeError,
    LLMChangeInterpreter,
)
from app.modules.company_knowledge.models.change_interpretation import (
    ChangeNarrative,
    SectionChangeInput,
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


@pytest.mark.asyncio
async def test_changed_section_returns_validated_narrative() -> None:
    provider = RecordingProvider(
        json.dumps(
            {
                "summary": "Pricing now includes a Pro plan.",
                "semantic_label": "pricing",
                "key_points": ["A Pro plan was added."],
            }
        )
    )
    interpreter = LLMChangeInterpreter(provider)
    change = SectionChangeInput.from_changed(
        before=make_section(1, "Starter plan"),
        after=make_section(2, "Starter and Pro plans"),
    )

    narrative = await interpreter.interpret(change)

    assert interpreter.prompt_version == "change-interpretation-v1"
    assert narrative == ChangeNarrative(
        summary="Pricing now includes a Pro plan.",
        semantic_label="pricing",
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
        '{"summary":"Careers were added.","semantic_label":"careers",'
        '"key_points":[]}'
    )
    interpreter = LLMChangeInterpreter(provider)
    change = SectionChangeInput.from_added(
        make_section(4, "Explore open roles")
    )

    await interpreter.interpret(change)

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
        '{"summary":" ","semantic_label":null,"key_points":[]}',
        '{"summary":"Removed.","semantic_label":" ","key_points":[]}',
        '{"summary":"Removed.","semantic_label":null,"key_points":[" "]}',
        (
            '{"summary":"Removed.","semantic_label":null,'
            '"key_points":[],"unsupported":true}'
        ),
    ],
)
async def test_invalid_provider_json_raises_change_context(
    response: str,
) -> None:
    interpreter = LLMChangeInterpreter(RecordingProvider(response))
    change = SectionChangeInput.from_removed(
        make_section(3, "Legacy plan")
    )

    with pytest.raises(
        InvalidChangeNarrativeError,
        match="removed section 3",
    ):
        await interpreter.interpret(change)
