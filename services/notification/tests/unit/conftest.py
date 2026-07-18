"""Unit tests for notification helpers — no DB (override parent clean_db)."""

import os

import pytest

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-pytest")
os.environ.setdefault("INTERNAL_API_KEY", "test-internal-key-for-pytest")


@pytest.fixture(autouse=True)
def clean_db():
    """Override root tests/conftest.py DB truncate for pure unit tests."""
    yield
