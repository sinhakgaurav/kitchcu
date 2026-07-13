"""Community service tests — TDD (Sprint 17)."""

import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://ckac:ckac_dev@localhost:15432/ckac")
os.environ.setdefault("DATABASE_SYNC_URL", "postgresql://ckac:ckac_dev@localhost:15432/ckac")
os.environ.setdefault("REDIS_URL", "redis://localhost:16379/0")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-pytest")
os.environ.setdefault("COMMUNITY_MIN_ORDERS_RANKING", "3")
os.environ.setdefault("APP_ENV", "test")

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import ckac_common.database as db_module

db_module.engine = create_async_engine(os.environ["DATABASE_URL"], poolclass=NullPool, echo=False)
db_module.SessionLocal = async_sessionmaker(db_module.engine, class_=AsyncSession, expire_on_commit=False)

import uuid
from datetime import UTC, datetime, timedelta

import psycopg2
import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from jose import jwt

from app.main import app
from tests.events_bootstrap import ensure_events_schema

SYNC_DB_URL = os.environ["DATABASE_SYNC_URL"]
JWT_SECRET = os.environ["JWT_SECRET"]


def _truncate_all() -> None:
    ensure_events_schema(SYNC_DB_URL)
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE ckac_community.chef_rankings CASCADE")
        cur.execute("TRUNCATE TABLE ckac_community.reward_redemptions CASCADE")
        cur.execute("TRUNCATE TABLE ckac_community.reward_point_ledger CASCADE")
        cur.execute("TRUNCATE TABLE ckac_community.kitchen_reward_balances CASCADE")
        cur.execute("TRUNCATE TABLE ckac_community.recipe_appreciations CASCADE")
        cur.execute("TRUNCATE TABLE ckac_community.shared_recipes CASCADE")
        cur.execute("TRUNCATE TABLE ckac_ratings.dish_rating_aggregates CASCADE")
        cur.execute("TRUNCATE TABLE ckac_orders.order_items CASCADE")
        cur.execute("TRUNCATE TABLE ckac_orders.order_status_events CASCADE")
        cur.execute("TRUNCATE TABLE ckac_orders.orders CASCADE")
        cur.execute("TRUNCATE TABLE ckac_identity.customers CASCADE")
        cur.execute("TRUNCATE TABLE ckac_identity.kitchens CASCADE")
        cur.execute("TRUNCATE TABLE ckac_identity.owners CASCADE")
        cur.execute("TRUNCATE TABLE ckac_events.outbox")
    conn.close()


async def _flush_streams() -> None:
    import redis.asyncio as redis

    client = redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
    try:
        await client.delete("ckac:community:recipe", "ckac:community:reward", "ckac:community:ranking")
    finally:
        await client.aclose()


def _make_owner_token(owner_id: uuid.UUID) -> str:
    expire = datetime.now(UTC) + timedelta(hours=1)
    return jwt.encode({"sub": str(owner_id), "type": "owner", "exp": expire}, JWT_SECRET, algorithm="HS256")


def _make_customer_token(customer_id: uuid.UUID) -> str:
    expire = datetime.now(UTC) + timedelta(hours=1)
    return jwt.encode({"sub": str(customer_id), "type": "customer", "exp": expire}, JWT_SECRET, algorithm="HS256")


def _seed_community_ctx() -> dict:
    owner_id = uuid.uuid4()
    kitchen_id = uuid.uuid4()
    customer_id = uuid.uuid4()
    dish_id = uuid.uuid4()
    phone = f"+919{owner_id.int % 900000000 + 100000000}"
    customer_phone = f"+919{customer_id.int % 900000000 + 100000000}"
    code = f"CKC{owner_id.hex[:4].upper()}"
    now = datetime.now(UTC)

    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO ckac_identity.owners (id, phone, name, subscription_tier, subscription_status) "
            "VALUES (%s::uuid, %s, 'Community Owner', 'starter', 'trial')",
            (str(owner_id), phone),
        )
        cur.execute(
            """
            INSERT INTO ckac_identity.kitchens
            (id, owner_id, code, name, city, state, location, status)
            VALUES (
                %s::uuid, %s::uuid, %s, 'Community Kitchen', 'Pune', 'Maharashtra',
                ST_SetSRID(ST_MakePoint(73.8958, 18.5362), 4326)::geography, 'active'
            )
            """,
            (str(kitchen_id), str(owner_id), code),
        )
        cur.execute(
            "INSERT INTO ckac_identity.customers (id, phone, name, status) VALUES (%s::uuid, %s, 'Fan', 'active')",
            (str(customer_id), customer_phone),
        )
        cur.execute(
            """
            INSERT INTO ckac_ratings.dish_rating_aggregates
            (id, kitchen_id, dish_id, rating_count, avg_home_taste, avg_quality, overall_rating)
            VALUES (%s::uuid, %s::uuid, %s::uuid, 12, 4.5, 4.3, 4.4)
            """,
            (str(uuid.uuid4()), str(kitchen_id), str(dish_id)),
        )
        for i in range(4):
            order_id = uuid.uuid4()
            cur.execute(
                """
                INSERT INTO ckac_orders.orders
                (id, kitchen_id, bill_id, order_code, status, source, delivery_type,
                 payment_method, customer_phone, subtotal, delivery_fee, total, created_at)
                VALUES (%s::uuid, %s::uuid, %s, %s, 'delivered', 'pwa', 'pickup', 'cod', %s, 200, 0, 200, %s)
                """,
                (
                    str(order_id),
                    str(kitchen_id),
                    f"BILL-COM-{i}",
                    f"{code}-BILL-COM-{i}",
                    customer_phone,
                    now - timedelta(days=i),
                ),
            )
    conn.close()

    return {
        "owner_id": owner_id,
        "kitchen_id": kitchen_id,
        "customer_id": customer_id,
        "owner_token": _make_owner_token(owner_id),
        "customer_token": _make_customer_token(customer_id),
    }


@pytest.fixture(autouse=True)
async def clean_db():
    _truncate_all()
    await _flush_streams()
    yield
    _truncate_all()
    await _flush_streams()


@pytest.fixture
async def client() -> AsyncClient:
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest.fixture
def community_ctx() -> dict:
    return _seed_community_ctx()
