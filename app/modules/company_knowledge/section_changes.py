"""Deterministic section change classification."""

from collections.abc import Sequence

from app.modules.company_knowledge.models.section_change import (
    SectionChange,
    SectionChangeSet,
)
from app.modules.company_knowledge.models.version import SectionVersion
from app.modules.company_knowledge.section_change_utils import (
    find_same_fingerprint_section,
    find_same_heading_section,
)


def classify_section_changes(
    previous_sections: Sequence[SectionVersion],
    current_sections: Sequence[SectionVersion],
) -> SectionChangeSet:
    """Classify added, removed, and changed sections between page versions."""
    remaining_previous = list(previous_sections)
    remaining_current = list(current_sections)

    remaining_previous, remaining_current = _exclude_unchanged_sections(
        remaining_previous,
        remaining_current,
    )

    changed_sections, remaining_previous, remaining_current = (
        _extract_changed_sections(
            remaining_previous,
            remaining_current,
        )
    )

    change_set = SectionChangeSet(
        added=tuple(remaining_current),
        removed=tuple(remaining_previous),
        changed=tuple(changed_sections),
    )
    return change_set


def _exclude_unchanged_sections(
    previous_sections: list[SectionVersion],
    current_sections: list[SectionVersion],
) -> tuple[list[SectionVersion], list[SectionVersion]]:
    """Return sections left after identical fingerprints are paired."""
    unmatched_previous: list[SectionVersion] = []
    unmatched_current = list(current_sections)

    for previous_section in previous_sections:
        current_section = find_same_fingerprint_section(
            previous_section,
            unmatched_current,
        )

        if current_section is None:
            unmatched_previous.append(previous_section)
        else:
            unmatched_current.remove(current_section)

    return unmatched_previous, unmatched_current


def _extract_changed_sections(
    previous_sections: list[SectionVersion],
    current_sections: list[SectionVersion],
) -> tuple[
    list[SectionChange],
    list[SectionVersion],
    list[SectionVersion],
]:
    """Pair changed sections that keep the same heading identity."""
    changed_sections: list[SectionChange] = []
    unmatched_previous: list[SectionVersion] = []
    unmatched_current = list(current_sections)

    for previous_section in previous_sections:
        current_section = find_same_heading_section(
            previous_section,
            unmatched_current,
        )

        if current_section is None:
            unmatched_previous.append(previous_section)
        else:
            changed_sections.append(
                SectionChange(
                    before=previous_section,
                    after=current_section,
                )
            )
            unmatched_current.remove(current_section)

    return changed_sections, unmatched_previous, unmatched_current
