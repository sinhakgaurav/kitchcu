"""Unit-test conftest — no Postgres/Redis required."""

import pytest


@pytest.fixture(autouse=True)
def clean_database():
    yield
