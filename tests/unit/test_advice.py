"""F7 tests: advice.json schema and guard test."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from leafcheck.advice import (
    advice_for,
    assert_advice_safe,
    load_advice,
)

ALL_19_CLASSES = [
    "Tomato_Bacterial_spot",
    "Tomato_Early_blight",
    "Tomato_Late_blight",
    "Tomato_Leaf_Mold",
    "Tomato_Septoria_leaf_spot",
    "Tomato_Spider_mites_Two_spotted_spider_mite",
    "Tomato__Target_Spot",
    "Tomato__Tomato_YellowLeaf__Curl_Virus",
    "Tomato__Tomato_mosaic_virus",
    "Tomato_healthy",
    "Potato___Early_blight",
    "Potato___Late_blight",
    "Potato___healthy",
    "Corn___Common_rust",
    "Corn___Gray_Leaf_Spot",
    "Corn___Northern_Leaf_Blight",
    "Corn___healthy",
    "Pepper__bell___Bacterial_spot",
    "Pepper__bell___healthy",
]


def _valid_advice() -> dict:
    out = {}
    for cls in ALL_19_CLASSES:
        out[cls] = {
            "en": f"Take a clear photo of a single {cls} leaf in good light. "
            f"Remove badly affected leaves and improve air flow. "
            f"Consult your local extension service for confirmation.",
            "bn": f"ভালো আলোতে একটি {cls} পাতার পরিষ্কার ছবি তুলুন। "
            f"খারাপভাবে আক্রান্ত পাতা সরিয়ে বায়ু চলাচল বাড়ান। "
            f"নিশ্চিতকরণের জন্য স্থানীয় কৃষি সেবার সাথে পরামর্শ করুন।",
            "reviewed_by_human": False,
        }
    return out


def test_advice_schema_all_classes_present(tmp_path: Path) -> None:
    """F7.AC1: all 19 classes have non-empty en + bn and reviewed_by_human."""
    p = tmp_path / "advice.json"
    p.write_text(json.dumps(_valid_advice()))
    db = load_advice(p)
    assert set(db.keys()) == set(ALL_19_CLASSES)
    for cls, entry in db.items():
        assert entry["en"], cls
        assert entry["bn"], cls
        assert "reviewed_by_human" in entry


def test_advice_guard_rejects_dose_pattern(tmp_path: Path) -> None:
    """F7.AC2: any dose pattern in advice text is rejected."""
    bad = _valid_advice()
    bad["Tomato_healthy"]["en"] = "Apply 5 ml of concentrate per liter of water."
    p = tmp_path / "advice.json"
    p.write_text(json.dumps(bad))
    db = load_advice(p)
    with pytest.raises(ValueError, match="dose"):
        assert_advice_safe(db)


def test_advice_guard_rejects_brand(tmp_path: Path) -> None:
    bad = _valid_advice()
    bad["Tomato_healthy"]["en"] = "Use Bayer product for best results."
    p = tmp_path / "advice.json"
    p.write_text(json.dumps(bad))
    db = load_advice(p)
    with pytest.raises(ValueError, match="brand"):
        assert_advice_safe(db)


def test_advice_for_returns_entry(tmp_path: Path) -> None:
    p = tmp_path / "advice.json"
    p.write_text(json.dumps(_valid_advice()))
    db = load_advice(p)
    out = advice_for(db, "Tomato_healthy")
    assert out is not None
    assert "en" in out and "bn" in out


def test_advice_for_missing_returns_none(tmp_path: Path) -> None:
    p = tmp_path / "advice.json"
    p.write_text(json.dumps(_valid_advice()))
    db = load_advice(p)
    assert advice_for(db, "Not_a_class") is None
