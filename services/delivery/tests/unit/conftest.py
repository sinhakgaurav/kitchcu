"""Unit tests — no DB."""

import os

import pytest

os.environ.setdefault("APP_ENV", "test")


@pytest.fixture(autouse=True)
def clean_db():
    yield
