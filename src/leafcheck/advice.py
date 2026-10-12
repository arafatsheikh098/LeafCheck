"""F7: load `data/advice.json` and surface per-class advice.

The advice file is keyed by class name (matching `models/class_names.json`).
Each entry has:
  - `en`: short English advice (≤ ~600 chars)
  - `bn`: short Bangla advice (same length budget)
  - `reviewed_by_human`: false by default; flipped to true after a human
    reviewer signs off on the text.

F7.AC2: this module is also the home of the dose-pattern guard that
rejects any string containing `\d+\s*(ml|mg|g/L|kg/ha)` or a brand word.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

DEFAULT_ADVICE_PATH = Path("data/advice.json")

DOSE_PATTERN = re.compile(r"\d+\s*(ml|mg|g/L|kg/ha)\b", re.IGNORECASE)
DEFAULT_BRAND_WORDS = [
    "Bayer",
    "Syngenta",
    "Monsanto",
    "Roundup",
    "Tilt",
    "Score",
    "Antracol",
    "Ridomil",
    "Dithane",
    "Mancozeb",
]


def load_advice(path: Path | str = DEFAULT_ADVICE_PATH) -> dict[str, dict[str, Any]]:
    """Load the advice JSON and return a class-name keyed dict.

    Raises FileNotFoundError if the file doesn't exist.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Missing {p}. Add a `data/advice.json` file (see README).")
    return json.loads(p.read_text())


def advice_for(advice_db: dict[str, dict[str, Any]], class_name: str) -> dict[str, Any] | None:
    """Return the advice entry for a class, or None if not present."""
    return advice_db.get(class_name)


def assert_advice_safe(
    advice_db: dict[str, dict[str, Any]],
    *,
    brand_words: list[str] | None = None,
) -> None:
    """F7.AC2: guard test helper.

    Raises ValueError if any advice text contains a dose pattern or a
    brand word. Intended to be called from a test, not at runtime.
    """
    brands = brand_words if brand_words is not None else DEFAULT_BRAND_WORDS
    for cls, entry in advice_db.items():
        for lang in ("en", "bn"):
            text = entry.get(lang, "")
            if DOSE_PATTERN.search(text):
                raise ValueError(f"advice for {cls!r} ({lang}) contains a dose pattern: {text!r}")
            for brand in brands:
                if brand.lower() in text.lower():
                    raise ValueError(f"advice for {cls!r} ({lang}) contains brand word {brand!r}")
