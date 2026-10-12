"""Shared pytest fixtures for the LeafCheck test suite.

The API predictor and advice DB are LRU-cached singletons (F5). Each
test that touches the API must start with a clean cache so a model
trained in tmp_path doesn't see a cached model from a prior test or
from the smoke `models/` dir on disk.
"""

from __future__ import annotations

import pytest

from leafcheck.api import reset_singletons


@pytest.fixture(autouse=True)
def _clear_singletons():
    """Wipe LRU caches before and after every test."""
    reset_singletons()
    yield
    reset_singletons()
