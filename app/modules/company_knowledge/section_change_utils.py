"""Small helpers used by deterministic section change matching."""

from collections.abc import Sequence

from app.modules.company_knowledge.models.version import SectionVersion


def find_same_fingerprint_section(
    reference_section: SectionVersion,
    sections: Sequence[SectionVersion],
) -> SectionVersion | None:
    """Find the closest section with identical content."""
    matching_sections = [
        section
        for section in sections
        if section.fingerprint == reference_section.fingerprint
    ]
    return _nearest_section(reference_section, matching_sections)


def find_same_heading_section(
    reference_section: SectionVersion,
    sections: Sequence[SectionVersion],
) -> SectionVersion | None:
    """Find the closest section with the same non-empty heading signature."""
    heading_signature = _heading_signature(reference_section)
    if heading_signature is None:
        return None

    matching_sections = [
        section
        for section in sections
        if _heading_signature(section) == heading_signature
    ]
    return _nearest_section(reference_section, matching_sections)


def _nearest_section(
    reference_section: SectionVersion,
    matching_sections: Sequence[SectionVersion],
) -> SectionVersion | None:
    """Return the closest candidate, or None when there is no match."""
    return min(
        matching_sections,
        default=None,
        key=lambda section: (
            abs(section.index - reference_section.index),
            section.index,
        ),
    )


def _heading_signature(
    section: SectionVersion,
) -> tuple[tuple[int, str], ...] | None:
    """Return ordered heading level/text pairs used as section identity."""
    if not section.headings:
        return None

    return tuple(
        (heading.level, heading.text)
        for heading in section.headings
    )
