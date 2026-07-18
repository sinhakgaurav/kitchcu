"""Unit-test conftest — no Postgres/Redis required."""

import pytest


@pytest.fixture(autouse=True)
async def clean_db():
    yield


@pytest.fixture(autouse=True)
def wire_wallet_and_notify_shims():
    yield
