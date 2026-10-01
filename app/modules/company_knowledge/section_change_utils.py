"""Small helpers used by deterministic section change matching."""

from collections.abc import Sequence

from app.modules.company_knowledge.models.version import SectionVersion


def find_same_fingerprint_section(
    reference_section: SectionVersion,
    sections: Sequence[SectionVersion],
) -> SectionVersion | None:
    """Return the first section with the same fingerprint."""
    return next(
        (
            section
            for section in sections
            if section.fingerprint == reference_section.fingerprint
        ),
        None,
    )


def find_same_heading_section(
    reference_section: SectionVersion,
    sections: Sequence[SectionVersion],
) -> SectionVersion | None:
    """Return the first section with the same non-empty heading signature."""
    heading_signature = _heading_signature(reference_section)
    if heading_signature is None:
        return None

    return next(
        (
            section
            for section in sections
            if _heading_signature(section) == heading_signature
        ),
        None,
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
