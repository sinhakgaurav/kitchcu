"""Unit tests under order/tests/unit — no Postgres required."""

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("APP_ENV", "test")

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def clean_db():
    """Override parent DB truncate fixture — unit tests are pure."""
    yield
