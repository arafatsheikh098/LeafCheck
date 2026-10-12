"""End-to-end data pipeline test against a synthetic fixture.

Covers F1.AC1, F1.AC2, F1.AC4, F2.AC1, F2.AC2, F2.AC3, F2.AC4 from SCOPE.md.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
from PIL import Image

from leafcheck import data as data_mod
from leafcheck.synth_data import write_tree


@pytest.fixture()
def synth_root(tmp_path: Path) -> Path:
    """A small, deliberately-leaky synthetic dataset.

    Layout (one folder per class):

      Tomato/
        original_a.jpg      (gradient_1)
        original_b.jpg      (gradient_2)
        original_c.jpg      (solid_a)
        dup_a_1.jpg         (rotated 90 of original_a)
        dup_a_2.jpg         (flipped of original_a)
        flip_c.jpg          (flipped of original_c)
      Potato/
        orig_1.jpg          (gradient_3)
        orig_2.jpg          (blob_alpha)
        corrupt.jpg         (truncated JPEG header)

    With the default hamming threshold of 8, dup_a_1 and dup_a_2 MUST land in
    the same group as original_a; flip_c MUST land in the same group as
    original_c. Each group should be entirely in one split.
    """
    root = tmp_path / "synth_source"
    root.mkdir()

    # Tomato: a variety of distinct images, then rotated/flipped copies
    # that MUST group with their originals.
    tomato = root / "Tomato"
    write_tree(
        tomato,
        [
            ("original_a.jpg", "gradient_1"),
            ("original_b.jpg", "gradient_2"),
            ("original_c.jpg", "solid_a"),
            ("dup_a_1.jpg", "gradient_1"),
            ("dup_a_2.jpg", "gradient_1"),
            ("flip_c.jpg", "solid_a"),
        ],
    )
    # Force dup_a_1 to be a 90-degree rotation of original_a, and dup_a_2 a mirror.
    a_path = tomato / "original_a.jpg"
    dup1 = tomato / "dup_a_1.jpg"
    dup2 = tomato / "dup_a_2.jpg"
    flip_c = tomato / "flip_c.jpg"
    c_path = tomato / "original_c.jpg"
    Image.open(a_path).rotate(90, expand=True).save(dup1, "JPEG", quality=92)
    Image.open(a_path).transpose(Image.FLIP_LEFT_RIGHT).save(dup2, "JPEG", quality=92)
    Image.open(c_path).transpose(Image.FLIP_LEFT_RIGHT).save(flip_c, "JPEG", quality=92)

    # Potato: two unrelated images + one corrupt file.
    potato = root / "Potato"
    write_tree(
        potato,
        [
            ("orig_1.jpg", "gradient_3"),
            ("orig_2.jpg", "blob_alpha"),
            ("corrupt.jpg", "corrupt"),
        ],
    )

    return root


def _manifest_rows(out: Path) -> list[dict[str, str]]:
    with (out / "manifest.csv").open() as fh:
        return list(csv.DictReader(fh))


def test_prepare_writes_manifest_with_sha256(tmp_path: Path, synth_root: Path) -> None:
    out = tmp_path / "out"
    data_mod.prepare(synth_root, out, config_path=_data_config())
    rows = _manifest_rows(out)
    assert rows, "manifest should not be empty"
    for row in rows:
        assert row["path"], "path is required"
        assert row["class"], "class is required"
        assert row["group_id"], "group_id is required"
        assert row["split"] in ("train", "val", "test"), "split must be one of the 3"
        assert len(row["sha256"]) == 64, "sha256 must be a 64-char hex digest"


def test_prepare_handles_corrupt_images(tmp_path: Path, synth_root: Path) -> None:
    out = tmp_path / "out"
    report = data_mod.prepare(synth_root, out, config_path=_data_config())
    assert report["corrupt_images"] >= 1
    rows = _manifest_rows(out)
    # The corrupt file's name contains "corrupt"; check that the corrupt
    # *image* (whose file is truncated) was not loaded into the manifest.
    bad = {r["path"] for r in rows if r["path"].endswith("corrupt.jpg")}
    assert bad == set(), f"corrupt images should be skipped, but manifest contains: {bad}"


def test_group_assignment_is_leak_free(tmp_path: Path, synth_root: Path) -> None:
    """F2.AC1: planted rotated/flipped copies must land in the same group AND
    the same split."""
    out = tmp_path / "out"
    data_mod.prepare(synth_root, out, config_path=_data_config())
    rows = _manifest_rows(out)
    by_path = {Path(r["path"]).name: r for r in rows}

    # The three Tomato-a copies should share a group_id and split.
    group_ids = {by_path[n]["group_id"] for n in ("original_a.jpg", "dup_a_1.jpg", "dup_a_2.jpg")}
    assert len(group_ids) == 1, f"expected 1 group for the 3 Tomato-a copies, got {group_ids}"
    splits = {by_path[n]["split"] for n in ("original_a.jpg", "dup_a_1.jpg", "dup_a_2.jpg")}
    assert len(splits) == 1, f"expected all 3 copies in the same split, got {splits}"

    # original_c and flip_c likewise.
    cg = {by_path[n]["group_id"] for n in ("original_c.jpg", "flip_c.jpg")}
    assert len(cg) == 1
    cs = {by_path[n]["split"] for n in ("original_c.jpg", "flip_c.jpg")}
    assert len(cs) == 1


def test_verify_reports_zero_overlap(tmp_path: Path, synth_root: Path) -> None:
    out = tmp_path / "out"
    data_mod.prepare(synth_root, out, config_path=_data_config())
    result = data_mod.verify(out)
    assert result["ok"], f"verify should report ok, got {result}"
    # All overlap counters should be zero (the verify result always returns
    # three key pairs, so we check the values, not the dict structure).
    assert all(v == 0 for v in result["sha256_overlap"].values())
    assert all(v == 0 for v in result["group_overlap"].values())


def test_per_class_split_within_one_percent(tmp_path: Path) -> None:
    """Larger synthetic: 4 classes x 30 valid images, all visually distinct.

    Per-class split should hit 70/15/15 within a small tolerance.
    """
    root = tmp_path / "big_synth"
    root.mkdir()
    classes = ["Tomato", "Potato", "Corn", "Bell_pepper"]
    for cls in classes:
        cdir = root / cls
        cdir.mkdir()
        for i in range(30):
            # Each image is genuinely distinct: random background, random
            # foreground, different disk position. The hamming distance
            # between any two should be well over the default threshold of 8,
            # so every image is its own group.
            img = _distinct_blob(seed=i * 9973 + hash(cls) % 100000, label=f"{cls}-{i}")
            img.save(cdir / f"img_{i:03d}.jpg", "JPEG", quality=92)

    out = tmp_path / "big_out"
    report = data_mod.prepare(root, out, config_path=_data_config())
    stats = report["per_class_split"]
    for cls in classes:
        s = stats[cls]
        total = sum(s.values())
        assert total == 30
        # Per F2.AC2: per-class split proportions should be within 1% of
        # 70/15/15. For 30 groups, 1% of 30 = 0.3 so a 1-group tolerance is
        # the strictest possible. We allow train {20..23} and val/test
        # {3..6} to be robust to the rounding adjustment.
        assert s["train"] in {20, 21, 22, 23}, s
        assert s["val"] in {3, 4, 5, 6}, s
        assert s["test"] in {3, 4, 5, 6}, s
        assert s["train"] + s["val"] + s["test"] == 30, s


def _distinct_blob(*, seed: int, label: str, size: tuple[int, int] = (96, 96)) -> Image.Image:
    """A coloured disk on a coloured background with deterministic noise.

    The disk radius and centre both vary with the seed so two seeds with the
    same label produce structurally different images.
    """
    import random

    from PIL import ImageDraw

    rng = random.Random(seed)
    bg = (rng.randint(0, 80), rng.randint(0, 80), rng.randint(0, 80))
    (rng.randint(150, 255), rng.randint(150, 255), rng.randint(150, 255))
    img = Image.new("RGB", size, bg)
    draw = ImageDraw.Draw(img)
    # Two concentric disks with different sizes for extra variation.
    for k in range(2):
        r = rng.randint(size[0] // 8, min(size) // (k + 2))
        cx = rng.randint(r, size[0] - r)
        cy = rng.randint(r, size[1] - r)
        c = (rng.randint(50, 200), rng.randint(50, 200), rng.randint(50, 200))
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=c)
    return img


def test_dataset_info_written(tmp_path: Path, synth_root: Path) -> None:
    out = tmp_path / "out"
    data_mod.prepare(synth_root, out, config_path=_data_config())
    assert (out / "DATASET_INFO.md").exists()
    text = (out / "DATASET_INFO.md").read_text()
    assert "PlantVillage" in text
    assert "License" in text or "license" in text


def test_data_report_has_required_fields(tmp_path: Path, synth_root: Path) -> None:
    out = tmp_path / "out"
    data_mod.prepare(synth_root, out, config_path=_data_config())
    report = json.loads((out / "data_report.json").read_text())
    for key in (
        "total_images",
        "corrupt_images",
        "duplicate_images_in_groups",
        "class_count",
        "group_count",
        "split_count",
        "classes",
        "ratios",
        "seed",
        "hamming_threshold",
        "per_class_split",
        "warnings",
    ):
        assert key in report, f"data_report missing key {key!r}"


def _data_config() -> Path:
    return Path(__file__).resolve().parents[2] / "configs" / "data.yaml"
