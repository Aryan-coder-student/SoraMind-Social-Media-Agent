"""Tests for deterministic section-level change classification."""

from app.modules.company_knowledge.change_detection.sections import (
    classify_section_changes,
)
from app.modules.company_knowledge.models.page import Heading
from app.modules.company_knowledge.models.version import SectionVersion


def make_section(
    *,
    index: int,
    heading: str | None,
    text: str,
    fingerprint: str,
) -> SectionVersion:
    """Build a persisted section snapshot for change-detection tests."""
    headings = (
        [Heading(level=2, text=heading)]
        if heading is not None
        else []
    )
    return SectionVersion(
        index=index,
        headings=headings,
        text=text,
        fingerprint=fingerprint,
    )


def test_identical_sections_produce_no_changes() -> None:
    previous = [
        make_section(
            index=0,
            heading="Hero",
            text="Welcome",
            fingerprint="a" * 64,
        )
    ]
    current = [
        make_section(
            index=0,
            heading="Hero",
            text="Welcome",
            fingerprint="a" * 64,
        )
    ]

    changes = classify_section_changes(previous, current)

    assert changes.added == ()
    assert changes.removed == ()
    assert changes.changed == ()


def test_new_section_is_classified_as_added() -> None:
    existing = make_section(
        index=0,
        heading="Hero",
        text="Welcome",
        fingerprint="a" * 64,
    )
    added = make_section(
        index=1,
        heading="Pricing",
        text="New plans",
        fingerprint="b" * 64,
    )

    changes = classify_section_changes([existing], [existing, added])

    assert changes.added == (added,)
    assert changes.removed == ()
    assert changes.changed == ()


def test_missing_section_is_classified_as_removed() -> None:
    retained = make_section(
        index=0,
        heading="Hero",
        text="Welcome",
        fingerprint="a" * 64,
    )
    removed = make_section(
        index=1,
        heading="Pricing",
        text="Old plans",
        fingerprint="b" * 64,
    )

    changes = classify_section_changes([retained, removed], [retained])

    assert changes.added == ()
    assert changes.removed == (removed,)
    assert changes.changed == ()


def test_same_heading_with_new_content_is_classified_as_changed() -> None:
    previous = make_section(
        index=1,
        heading="Pricing",
        text="Old plans",
        fingerprint="a" * 64,
    )
    current = make_section(
        index=1,
        heading="Pricing",
        text="New plans",
        fingerprint="b" * 64,
    )

    changes = classify_section_changes([previous], [current])

    assert changes.added == ()
    assert changes.removed == ()
    assert len(changes.changed) == 1
    assert changes.changed[0].before == previous
    assert changes.changed[0].after == current


def test_same_position_can_match_changed_heading() -> None:
    previous = make_section(
        index=0,
        heading="Plans",
        text="Choose a plan",
        fingerprint="a" * 64,
    )
    current = make_section(
        index=0,
        heading="Pricing",
        text="Choose the right plan",
        fingerprint="b" * 64,
    )

    changes = classify_section_changes([previous], [current])

    assert len(changes.changed) == 1
    assert changes.changed[0].before == previous
    assert changes.changed[0].after == current


def test_unchanged_reordered_sections_are_not_reported_as_changes() -> None:
    hero = make_section(
        index=0,
        heading="Hero",
        text="Welcome",
        fingerprint="a" * 64,
    )
    pricing = make_section(
        index=1,
        heading="Pricing",
        text="Plans",
        fingerprint="b" * 64,
    )
    reordered_pricing = pricing.model_copy(update={"index": 0})
    reordered_hero = hero.model_copy(update={"index": 1})

    changes = classify_section_changes(
        [hero, pricing],
        [reordered_pricing, reordered_hero],
    )

    assert changes.added == ()
    assert changes.removed == ()
    assert changes.changed == ()


def test_inserted_section_does_not_make_shifted_sections_look_changed() -> None:
    hero = make_section(
        index=0,
        heading="Hero",
        text="Welcome",
        fingerprint="a" * 64,
    )
    pricing = make_section(
        index=1,
        heading="Pricing",
        text="Plans",
        fingerprint="b" * 64,
    )
    inserted = make_section(
        index=0,
        heading="Announcement",
        text="Launch",
        fingerprint="c" * 64,
    )

    changes = classify_section_changes(
        [hero, pricing],
        [
            inserted,
            hero.model_copy(update={"index": 1}),
            pricing.model_copy(update={"index": 2}),
        ],
    )

    assert changes.added == (inserted,)
    assert changes.removed == ()
    assert changes.changed == ()


def test_moved_section_with_same_heading_and_new_content_is_changed() -> None:
    hero = make_section(
        index=0,
        heading="Hero",
        text="Welcome",
        fingerprint="a" * 64,
    )
    pricing = make_section(
        index=1,
        heading="Pricing",
        text="Old plans",
        fingerprint="b" * 64,
    )
    changed_pricing = make_section(
        index=0,
        heading="Pricing",
        text="New plans",
        fingerprint="c" * 64,
    )
    moved_hero = hero.model_copy(update={"index": 1})

    changes = classify_section_changes(
        [hero, pricing],
        [changed_pricing, moved_hero],
    )

    assert changes.added == ()
    assert changes.removed == ()
    assert len(changes.changed) == 1
    assert changes.changed[0].before == pricing
    assert changes.changed[0].after == changed_pricing


def test_duplicate_headings_match_exact_content_before_changed_content() -> None:
    first = make_section(
        index=0,
        heading="Feature",
        text="Alpha",
        fingerprint="a" * 64,
    )
    second = make_section(
        index=1,
        heading="Feature",
        text="Beta",
        fingerprint="b" * 64,
    )
    unchanged_second = second.model_copy(update={"index": 0})
    changed_first = make_section(
        index=1,
        heading="Feature",
        text="Alpha updated",
        fingerprint="c" * 64,
    )

    changes = classify_section_changes(
        [first, second],
        [unchanged_second, changed_first],
    )

    assert len(changes.changed) == 1
    assert changes.changed[0].before == first
    assert changes.changed[0].after == changed_first


def test_change_results_are_ordered_by_section_position() -> None:
    old_later = make_section(
        index=3,
        heading="Later",
        text="Old later",
        fingerprint="a" * 64,
    )
    old_earlier = make_section(
        index=1,
        heading="Earlier",
        text="Old earlier",
        fingerprint="b" * 64,
    )
    new_later = make_section(
        index=3,
        heading="Later",
        text="New later",
        fingerprint="c" * 64,
    )
    new_earlier = make_section(
        index=1,
        heading="Earlier",
        text="New earlier",
        fingerprint="d" * 64,
    )

    changes = classify_section_changes(
        [old_later, old_earlier],
        [new_later, new_earlier],
    )

    assert [change.after.index for change in changes.changed] == [1, 3]
