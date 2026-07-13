"""Delivery service tests — TDD (Sprint 13)."""

import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://ckac:ckac_dev@localhost:15432/ckac")
os.environ.setdefault("DATABASE_SYNC_URL", "postgresql://ckac:ckac_dev@localhost:15432/ckac")
os.environ.setdefault("REDIS_URL", "redis://localhost:16379/0")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-pytest")
os.environ.setdefault("APP_ENV", "test")

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import ckac_common.database as db_module

db_module.engine = create_async_engine(os.environ["DATABASE_URL"], poolclass=NullPool, echo=False)
db_module.SessionLocal = async_sessionmaker(
    db_module.engine, class_=AsyncSession, expire_on_commit=False
)

import uuid

import psycopg2
import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from app.main import app
from tests.events_bootstrap import ensure_events_schema

SYNC_DB_URL = os.environ["DATABASE_SYNC_URL"]


def _truncate_all() -> None:
    ensure_events_schema(SYNC_DB_URL)
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE ckac_delivery.delivery_quotes CASCADE")
        cur.execute("TRUNCATE TABLE ckac_orders.order_items CASCADE")
        cur.execute("TRUNCATE TABLE ckac_orders.orders CASCADE")
        cur.execute("TRUNCATE TABLE ckac_identity.kitchens CASCADE")
        cur.execute("TRUNCATE TABLE ckac_identity.owners CASCADE")
        cur.execute("TRUNCATE TABLE ckac_events.outbox")
    conn.close()


async def _flush_delivery_streams() -> None:
    import redis.asyncio as redis

    client = redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
    try:
        await client.delete("ckac:delivery:quote", "ckac:delivery:tracking")
    finally:
        await client.aclose()


def _seed_kitchen() -> dict:
    owner_id = uuid.uuid4()
    kitchen_id = uuid.uuid4()
    phone = f"+919{owner_id.int % 900000000 + 100000000}"
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ckac_identity.owners (id, phone, name, subscription_tier, subscription_status)
            VALUES (%s::uuid, %s, 'Delivery Owner', 'starter', 'trial')
            """,
            (str(owner_id), phone),
        )
        cur.execute(
            """
            INSERT INTO ckac_identity.kitchens
            (id, owner_id, code, name, location, status,
             free_delivery_radius_km, max_delivery_radius_km)
            VALUES (
                %s::uuid, %s::uuid, %s, 'Delivery Kitchen',
                ST_SetSRID(ST_MakePoint(73.8958, 18.5362), 4326)::geography,
                'active', 3.0, 10.0
            )
            """,
            (str(kitchen_id), str(owner_id), f"CKD{owner_id.hex[:4].upper()}"),
        )
    conn.close()
    return {
        "kitchen_id": kitchen_id,
        "lat": 18.5362,
        "lng": 73.8958,
        "near_lat": 18.57,
        "near_lng": 73.93,
        "far_lat": 18.70,
        "far_lng": 74.10,
    }


@pytest.fixture(autouse=True)
async def clean_db():
    _truncate_all()
    await _flush_delivery_streams()
    yield
    _truncate_all()
    await _flush_delivery_streams()


@pytest.fixture
async def client() -> AsyncClient:
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest.fixture
def delivery_ctx() -> dict:
    return _seed_kitchen()
