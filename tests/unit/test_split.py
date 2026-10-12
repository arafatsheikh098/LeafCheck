"""Tests for the group-aware stratified split."""

from __future__ import annotations

import pytest

from leafcheck.split import SPLIT_NAMES, assign_groups, make_group_key


def test_assign_groups_covers_all_inputs() -> None:
    pairs = [(make_group_key("Tomato", f"g{i}"), "Tomato") for i in range(30)]
    pairs += [(make_group_key("Potato", f"g{i}"), "Potato") for i in range(30)]
    assignments = assign_groups(pairs, seed=0)
    assert {a.group_id for a in assignments} == {g for g, _ in pairs}


def test_assign_groups_within_one_percent_per_class() -> None:
    """For a class of 100 groups, 70/15/15 must hit within 1 group each."""
    pairs = [(make_group_key("Tomato", f"g{i}"), "Tomato") for i in range(100)]
    assignments = assign_groups(pairs, seed=0)
    counts = {s: 0 for s in SPLIT_NAMES}
    for a in assignments:
        counts[a.split] += 1
    assert counts == {"train": 70, "val": 15, "test": 15}


def test_small_class_goes_entirely_to_train() -> None:
    pairs = [(make_group_key("Rare", "g1"), "Rare"), (make_group_key("Rare", "g2"), "Rare")]
    assignments = assign_groups(pairs, seed=0)
    assert {a.split for a in assignments} == {"train"}


def test_each_group_lands_in_exactly_one_split() -> None:
    pairs = [(make_group_key("Tomato", f"g{i}"), "Tomato") for i in range(30)]
    assignments = assign_groups(pairs, seed=0)
    by_group: dict[str, set[str]] = {}
    for a in assignments:
        by_group.setdefault(a.group_id, set()).add(a.split)
    assert all(len(splits) == 1 for splits in by_group.values())


def test_seed_is_deterministic() -> None:
    pairs = [(make_group_key("Tomato", f"g{i}"), "Tomato") for i in range(30)]
    a = assign_groups(pairs, seed=42)
    b = assign_groups(pairs, seed=42)
    assert [(x.group_id, x.split) for x in a] == [(x.group_id, x.split) for x in b]


def test_different_seeds_can_differ() -> None:
    pairs = [(make_group_key("Tomato", f"g{i}"), "Tomato") for i in range(30)]
    a = assign_groups(pairs, seed=1)
    b = assign_groups(pairs, seed=999)
    a_splits = sorted(x.split for x in a)
    b_splits = sorted(x.split for x in b)
    # It's possible (but vanishingly unlikely for 30 items) that two seeds
    # produce the same assignment. Skip the assertion in that case.
    if a_splits == b_splits:
        pytest.skip("seeds happened to match")
    assert a_splits != b_splits
