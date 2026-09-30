"""Deterministic section matching and change classification."""

from collections.abc import Sequence

from app.modules.company_knowledge.models.change import (
    SectionChange,
    SectionChangeSet,
)
from app.modules.company_knowledge.models.version import SectionVersion


def classify_section_changes(
    previous_sections: Sequence[SectionVersion],
    current_sections: Sequence[SectionVersion],
) -> SectionChangeSet:
    """Classify added, removed, and changed sections between page versions."""
    remaining_previous = sorted(
        previous_sections,
        key=lambda section: section.index,
    )
    remaining_current = sorted(
        current_sections,
        key=lambda section: section.index,
    )

    _remove_unchanged_sections(
        remaining_previous,
        remaining_current,
    )

    changed_sections = _match_changed_sections(
        remaining_previous,
        remaining_current,
    )

    return SectionChangeSet(
        added=tuple(remaining_current),
        removed=tuple(remaining_previous),
        changed=tuple(
            sorted(
                changed_sections,
                key=lambda change: change.after.index,
            )
        ),
    )


def _remove_unchanged_sections(
    previous_sections: list[SectionVersion],
    current_sections: list[SectionVersion],
) -> None:
    """Remove sections with identical fingerprints from both working lists."""
    for previous_section in previous_sections.copy():
        matching_sections = [
            current_section
            for current_section in current_sections
            if current_section.fingerprint == previous_section.fingerprint
        ]
        if not matching_sections:
            continue

        current_section = _nearest_section(
            previous_section,
            matching_sections,
        )
        previous_sections.remove(previous_section)
        current_sections.remove(current_section)


def _match_changed_sections(
    previous_sections: list[SectionVersion],
    current_sections: list[SectionVersion],
) -> list[SectionChange]:
    """Match changed sections only when their heading identity is preserved."""
    changes: list[SectionChange] = []

    for previous_section in previous_sections.copy():
        heading_signature = _heading_signature(previous_section)
        if heading_signature is None:
            continue

        matching_sections = [
            current_section
            for current_section in current_sections
            if _heading_signature(current_section) == heading_signature
        ]
        if not matching_sections:
            continue

        current_section = _nearest_section(
            previous_section,
            matching_sections,
        )
        previous_sections.remove(previous_section)
        current_sections.remove(current_section)
        changes.append(
            SectionChange(
                before=previous_section,
                after=current_section,
            )
        )

    return changes


def _nearest_section(
    reference_section: SectionVersion,
    matching_sections: Sequence[SectionVersion],
) -> SectionVersion:
    """Choose the closest matching section in a deterministic way."""
    return min(
        matching_sections,
        key=lambda section: (
            abs(section.index - reference_section.index),
            section.index,
        ),
    )


def _heading_signature(
    section: SectionVersion,
) -> tuple[tuple[int, str], ...] | None:
    """Return the ordered heading level/text signature for a section."""
    if not section.headings:
        return None

    return tuple(
        (heading.level, heading.text)
        for heading in section.headings
    )
