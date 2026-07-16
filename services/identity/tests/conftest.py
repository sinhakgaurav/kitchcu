"""Pytest configuration — set env and test engine before application imports."""

import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://ckac:ckac_dev@localhost:15432/ckac",
)
os.environ.setdefault(
    "DATABASE_SYNC_URL",
    "postgresql://ckac:ckac_dev@localhost:15432/ckac",
)
os.environ.setdefault("REDIS_URL", "redis://localhost:16379/0")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-pytest")
os.environ.setdefault("INTERNAL_API_KEY", "test-internal-key-for-pytest")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("MEDIA_STORAGE_BACKEND", "local")

# NullPool avoids asyncpg connections being reused across pytest event loops (Windows).
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import ckac_common.database as db_module

db_module.engine = create_async_engine(
    os.environ["DATABASE_URL"],
    poolclass=NullPool,
    echo=False,
)
db_module.SessionLocal = async_sessionmaker(
    db_module.engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

import uuid

import psycopg2
import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.customer_schemas import clear_customer_otp_store
from app.routes import _DEV_OTP

from tests.events_bootstrap import ensure_events_schema

SYNC_DB_URL = os.environ["DATABASE_SYNC_URL"]


def _truncate_tables() -> None:
    ensure_events_schema(SYNC_DB_URL)
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(
                "TRUNCATE TABLE ckac_identity.customer_oauth_identities, "
                "ckac_identity.customers, ckac_identity.kitchens, ckac_identity.owners "
                "RESTART IDENTITY CASCADE"
            )
            cur.execute("TRUNCATE TABLE ckac_events.outbox")
    finally:
        conn.close()


@pytest.fixture(autouse=True)
def clean_database():
    """Reset identity tables and OTP store between tests."""
    _DEV_OTP.clear()
    clear_customer_otp_store()
    _truncate_tables()
    yield
    _DEV_OTP.clear()
    clear_customer_otp_store()


@pytest.fixture
async def client() -> AsyncClient:
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest.fixture
def unique_phone() -> str:
    """10-digit local number — normalized to +91 by API."""
    return str(uuid.uuid4().int % 9000000000 + 1000000000)


@pytest.fixture
async def registered_owner(client: AsyncClient, unique_phone: str) -> dict:
    response = await client.post(
        "/api/v1/owners/register",
        json={"phone": unique_phone, "name": "Test Owner", "email": "owner@test.com"},
    )
    assert response.status_code == 201
    return response.json()


@pytest.fixture
async def auth_token(client: AsyncClient, registered_owner: dict) -> str:
    phone = registered_owner["phone"]
    await client.post("/api/v1/auth/otp/request", json={"phone": phone})
    response = await client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": phone, "otp": "123456"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
async def auth_headers(auth_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {auth_token}"}
