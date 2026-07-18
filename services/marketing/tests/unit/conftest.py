"""Unit-test conftest — no Postgres/Redis required."""

import pytest


@pytest.fixture(autouse=True)
async def clean_db():
    yield
