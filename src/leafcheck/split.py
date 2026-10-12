"""Group-aware stratified split.

The classical `train_test_split` will happily put two near-duplicates of the
same leaf on different sides of the split, which leaks train signal into
validation/test. We work at the **group** level: every group lives entirely
in one of {train, val, test}, and the per-class ratio of (groups-in-split /
groups-in-class) is as close to 70/15/15 as we can get.

For tiny classes (fewer than 3 groups) we put the whole class in train and
log a warning, since otherwise we'd have val/test groups of size 1 which
makes the leak test tautological.
"""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass

SPLIT_NAMES = ("train", "val", "test")
SPLIT_RATIOS = {"train": 0.70, "val": 0.15, "test": 0.15}


@dataclass(frozen=True)
class GroupAssignment:
    group_id: str
    class_name: str
    split: str  # one of SPLIT_NAMES


def assign_groups(
    groups: list[tuple[str, str]],
    *,
    ratios: dict[str, float] = SPLIT_RATIOS,
    seed: int = 42,
    min_groups_for_split: int = 3,
) -> list[GroupAssignment]:
    """Assign each (group_id, class_name) to a single split, stratified per class.

    `groups` is a list of `(group_id, class_name)` pairs. Group ids are unique
    per (class_name, group_id) — i.e. a group "leaf_42" appearing under both
    "Tomato" and "Potato" must be passed as two entries with different group
    ids (we use `<class>::<group>` internally; see `make_group_key`).
    """
    if set(ratios) != set(SPLIT_NAMES) or abs(sum(ratios.values()) - 1.0) > 1e-6:
        raise ValueError(f"ratios must sum to 1.0 over {SPLIT_NAMES}")

    by_class: dict[str, list[str]] = defaultdict(list)
    for group_id, class_name in groups:
        by_class[class_name].append(group_id)

    rng = random.Random(seed)
    out: list[GroupAssignment] = []

    for class_name, ids in by_class.items():
        ids = sorted(set(ids))  # de-dup
        rng.shuffle(ids)

        if len(ids) < min_groups_for_split:
            # Whole class into train; no val/test leakage because there are no
            # near-duplicate groups elsewhere (group ids are unique per class).
            for gid in ids:
                out.append(GroupAssignment(gid, class_name, "train"))
            continue

        n = len(ids)
        # Greedy round-robin by target share to hit 70/15/15 within ±1 group.
        targets = {name: round(n * r) for name, r in ratios.items()}
        # Adjust rounding so the totals match exactly.
        diff = n - sum(targets.values())
        if diff != 0:
            # Push the difference into the largest split.
            biggest = max(targets, key=targets.get)
            targets[biggest] += diff

        cursor = 0
        for name in SPLIT_NAMES:  # deterministic order: train, val, test
            take = targets[name]
            for gid in ids[cursor : cursor + take]:
                out.append(GroupAssignment(gid, class_name, name))
            cursor += take

    return out


def make_group_key(class_name: str, raw_group_id: str) -> str:
    """Make group ids unique per class so cross-class groups can't collide."""
    return f"{class_name}::{raw_group_id}"
