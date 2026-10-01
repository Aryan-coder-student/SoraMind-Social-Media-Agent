"""Tests for deterministic section-level change classification."""

from app.modules.company_knowledge.section_changes import (
    classify_section_changes,
)
from app.modules.company_knowledge.models.page import Heading
from app.modules.company_knowledge.models.version import SectionVersion


def make_section(
    index: int,
    heading: str | None,
    fingerprint: str,
    text: str | None = None,
) -> SectionVersion:
    """Build one persisted section snapshot."""
    headings = [] if heading is None else [Heading(level=2, text=heading)]
    return SectionVersion(
        index=index,
        headings=headings,
        text=text if text is not None else heading or "section",
        fingerprint=fingerprint,
    )


def test_identical_sections_have_no_reported_changes() -> None:
    hero = make_section(0, "Hero", "a" * 64)

    changes = classify_section_changes([hero], [hero])

    assert changes.added == ()
    assert changes.removed == ()
    assert changes.changed == ()


def test_new_section_is_added() -> None:
    hero = make_section(0, "Hero", "a" * 64)
    pricing = make_section(1, "Pricing", "b" * 64)

    changes = classify_section_changes([hero], [hero, pricing])

    assert changes.added == (pricing,)
    assert changes.removed == ()
    assert changes.changed == ()


def test_missing_section_is_removed() -> None:
    hero = make_section(0, "Hero", "a" * 64)
    pricing = make_section(1, "Pricing", "b" * 64)

    changes = classify_section_changes([hero, pricing], [hero])

    assert changes.added == ()
    assert changes.removed == (pricing,)
    assert changes.changed == ()


def test_same_heading_with_new_content_is_changed() -> None:
    previous_pricing = make_section(
        1,
        "Pricing",
        "a" * 64,
        text="Old plans",
    )
    current_pricing = make_section(
        1,
        "Pricing",
        "b" * 64,
        text="New plans",
    )

    changes = classify_section_changes(
        [previous_pricing],
        [current_pricing],
    )

    assert changes.added == ()
    assert changes.removed == ()
    assert len(changes.changed) == 1
    assert changes.changed[0].before == previous_pricing
    assert changes.changed[0].after == current_pricing


def test_same_position_with_different_heading_is_replacement() -> None:
    previous_section = make_section(0, "Pricing", "a" * 64)
    current_section = make_section(0, "Careers", "b" * 64)

    changes = classify_section_changes(
        [previous_section],
        [current_section],
    )

    assert changes.added == (current_section,)
    assert changes.removed == (previous_section,)
    assert changes.changed == ()


def test_changed_section_without_heading_is_replacement() -> None:
    previous_section = make_section(0, None, "a" * 64, text="Old")
    current_section = make_section(0, None, "b" * 64, text="New")

    changes = classify_section_changes(
        [previous_section],
        [current_section],
    )

    assert changes.added == (current_section,)
    assert changes.removed == (previous_section,)
    assert changes.changed == ()


def test_reordered_unchanged_sections_have_no_reported_changes() -> None:
    hero = make_section(0, "Hero", "a" * 64)
    pricing = make_section(1, "Pricing", "b" * 64)

    changes = classify_section_changes(
        [hero, pricing],
        [
            pricing.model_copy(update={"index": 0}),
            hero.model_copy(update={"index": 1}),
        ],
    )

    assert changes.added == ()
    assert changes.removed == ()
    assert changes.changed == ()


def test_inserted_section_does_not_change_shifted_sections() -> None:
    hero = make_section(0, "Hero", "a" * 64)
    pricing = make_section(1, "Pricing", "b" * 64)
    announcement = make_section(0, "Announcement", "c" * 64)

    changes = classify_section_changes(
        [hero, pricing],
        [
            announcement,
            hero.model_copy(update={"index": 1}),
            pricing.model_copy(update={"index": 2}),
        ],
    )

    assert changes.added == (announcement,)
    assert changes.removed == ()
    assert changes.changed == ()


def test_exact_content_is_matched_before_duplicate_heading() -> None:
    first_feature = make_section(0, "Feature", "a" * 64, text="Alpha")
    second_feature = make_section(1, "Feature", "b" * 64, text="Beta")
    unchanged_second = second_feature.model_copy(update={"index": 0})
    changed_first = make_section(
        1,
        "Feature",
        "c" * 64,
        text="Alpha updated",
    )

    changes = classify_section_changes(
        [first_feature, second_feature],
        [unchanged_second, changed_first],
    )

    assert len(changes.changed) == 1
    assert changes.changed[0].before == first_feature
    assert changes.changed[0].after == changed_first
