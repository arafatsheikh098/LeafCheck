"""F5: FastAPI dependency singletons.

The predictor and the advice database are loaded once at app startup
(F5.AC3) and shared across all requests. `get_predictor` and
`get_advice` are FastAPI dependencies that return the same instance.
The model dir and advice path default to the `LEAFCHECK_MODEL_DIR` /
`LEAFCHECK_ADVICE_PATH` environment variables, with `models/` and
`data/advice.json` as fallbacks.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from leafcheck.advice import load_advice
from leafcheck.predictor import Predictor


@lru_cache(maxsize=4)
def _load_predictor_cached(model_dir_str: str) -> Predictor:
    return Predictor(Path(model_dir_str))


@lru_cache(maxsize=4)
def _load_advice_cached(advice_path_str: str) -> dict:
    return load_advice(advice_path_str)


def default_model_dir() -> Path:
    """Resolve the model dir from LEAFCHECK_MODEL_DIR, else 'models'."""
    p = os.environ.get("LEAFCHECK_MODEL_DIR")
    return Path(p) if p else Path("models")


def default_advice_path() -> Path:
    """Resolve the advice path from LEAFCHECK_ADVICE_PATH, else 'data/advice.json'."""
    p = os.environ.get("LEAFCHECK_ADVICE_PATH")
    return Path(p) if p else Path("data/advice.json")


def get_predictor(model_dir: Path | None = None) -> Predictor:
    """Return the singleton Predictor. Used as a FastAPI dependency."""
    md = model_dir or default_model_dir()
    return _load_predictor_cached(str(md.resolve()))


def get_advice(advice_path: Path | None = None) -> dict:
    """Return the singleton advice database. Used as a FastAPI dependency."""
    p = advice_path or default_advice_path()
    return _load_advice_cached(str(p.resolve()))


def reset_singletons() -> None:
    """Clear the LRU caches (test helper)."""
    _load_predictor_cached.cache_clear()
    _load_advice_cached.cache_clear()
