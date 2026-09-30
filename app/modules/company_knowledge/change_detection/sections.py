"""Deterministic section matching and change classification."""

from collections.abc import Sequence

from app.modules.company_knowledge.models.change import (
    SectionChange,
    SectionChangeSet,
)
from app.modules.company_knowledge.models.version import SectionVersion


def classify_section_changes(
    previous: Sequence[SectionVersion],
    current: Sequence[SectionVersion],
) -> SectionChangeSet:
    """Classify added, removed, and changed sections.

    Matching is intentionally deterministic and conservative:

    1. identical fingerprints match first, regardless of position;
    2. remaining sections with the same non-empty heading signature match;
    3. remaining sections at the same position match;
    4. unmatched previous/current sections are removed/added.

    Exact fingerprint matching first prevents insertions, removals, and simple
    reordering from being misclassified as content changes.
    """
    previous_sections = tuple(sorted(previous, key=_section_sort_key))
    current_sections = tuple(sorted(current, key=_section_sort_key))

    _validate_unique_indexes(previous_sections, "previous")
    _validate_unique_indexes(current_sections, "current")

    unmatched_previous = set(range(len(previous_sections)))
    unmatched_current = set(range(len(current_sections)))

    _consume_exact_fingerprint_matches(
        previous_sections,
        current_sections,
        unmatched_previous,
        unmatched_current,
    )

    changed_pairs: list[tuple[int, int]] = []

    changed_pairs.extend(
        _consume_heading_matches(
            previous_sections,
            current_sections,
            unmatched_previous,
            unmatched_current,
        )
    )
    changed_pairs.extend(
        _consume_position_matches(
            previous_sections,
            current_sections,
            unmatched_previous,
            unmatched_current,
        )
    )

    changed = tuple(
        sorted(
            (
                SectionChange(
                    before=previous_sections[previous_index],
                    after=current_sections[current_index],
                )
                for previous_index, current_index in changed_pairs
            ),
            key=lambda change: (
                change.after.index,
                change.before.index,
            ),
        )
    )
    removed = tuple(
        previous_sections[index]
        for index in sorted(
            unmatched_previous,
            key=lambda index: _section_sort_key(previous_sections[index]),
        )
    )
    added = tuple(
        current_sections[index]
        for index in sorted(
            unmatched_current,
            key=lambda index: _section_sort_key(current_sections[index]),
        )
    )

    return SectionChangeSet(
        added=added,
        removed=removed,
        changed=changed,
    )


def _consume_exact_fingerprint_matches(
    previous: tuple[SectionVersion, ...],
    current: tuple[SectionVersion, ...],
    unmatched_previous: set[int],
    unmatched_current: set[int],
) -> None:
    """Consume unchanged sections before any identity heuristics are used."""
    for previous_index in _ordered_indexes(unmatched_previous, previous):
        previous_section = previous[previous_index]
        candidates = [
            current_index
            for current_index in unmatched_current
            if current[current_index].fingerprint == previous_section.fingerprint
        ]
        if not candidates:
            continue

        current_index = _nearest_candidate(
            previous_section,
            candidates,
            current,
        )
        unmatched_previous.remove(previous_index)
        unmatched_current.remove(current_index)


def _consume_heading_matches(
    previous: tuple[SectionVersion, ...],
    current: tuple[SectionVersion, ...],
    unmatched_previous: set[int],
    unmatched_current: set[int],
) -> list[tuple[int, int]]:
    """Match changed sections that still have the same heading identity."""
    matches: list[tuple[int, int]] = []

    for previous_index in _ordered_indexes(unmatched_previous, previous):
        previous_section = previous[previous_index]
        signature = _heading_signature(previous_section)
        if signature is None:
            continue

        candidates = [
            current_index
            for current_index in unmatched_current
            if _heading_signature(current[current_index]) == signature
        ]
        if not candidates:
            continue

        current_index = _nearest_candidate(
            previous_section,
            candidates,
            current,
        )
        unmatched_previous.remove(previous_index)
        unmatched_current.remove(current_index)
        matches.append((previous_index, current_index))

    return matches


def _consume_position_matches(
    previous: tuple[SectionVersion, ...],
    current: tuple[SectionVersion, ...],
    unmatched_previous: set[int],
    unmatched_current: set[int],
) -> list[tuple[int, int]]:
    """Match remaining replacements that occupy the same section position."""
    current_by_position = {
        current[index].index: index
        for index in unmatched_current
    }
    matches: list[tuple[int, int]] = []

    for previous_index in _ordered_indexes(unmatched_previous, previous):
        current_index = current_by_position.get(
            previous[previous_index].index
        )
        if current_index is None or current_index not in unmatched_current:
            continue

        unmatched_previous.remove(previous_index)
        unmatched_current.remove(current_index)
        matches.append((previous_index, current_index))

    return matches


def _nearest_candidate(
    section: SectionVersion,
    candidates: Sequence[int],
    candidate_sections: tuple[SectionVersion, ...],
) -> int:
    """Choose one deterministic candidate, preferring the closest position."""
    return min(
        candidates,
        key=lambda candidate_index: (
            abs(
                section.index
                - candidate_sections[candidate_index].index
            ),
            candidate_sections[candidate_index].index,
            candidate_index,
        ),
    )


def _ordered_indexes(
    indexes: set[int],
    sections: tuple[SectionVersion, ...],
) -> list[int]:
    """Return unmatched tuple indexes in stable page order."""
    return sorted(
        indexes,
        key=lambda index: _section_sort_key(sections[index]),
    )


def _section_sort_key(section: SectionVersion) -> tuple[int, str]:
    """Sort persisted sections deterministically."""
    return section.index, section.fingerprint


def _heading_signature(
    section: SectionVersion,
) -> tuple[tuple[int, str], ...] | None:
    """Return a stable heading signature when a section has headings."""
    if not section.headings:
        return None

    return tuple(
        (heading.level, heading.text)
        for heading in section.headings
    )


def _validate_unique_indexes(
    sections: Sequence[SectionVersion],
    version_name: str,
) -> None:
    """Reject invalid version snapshots with duplicate section positions."""
    indexes = [section.index for section in sections]
    if len(indexes) != len(set(indexes)):
        raise ValueError(
            f"{version_name} sections must have unique indexes"
        )
