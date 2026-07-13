"""Order service tests — TDD (Sprint 3)."""

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
os.environ.setdefault("NOTIFICATION_SERVICE_URL", "http://test")
os.environ.setdefault("CATALOG_SERVICE_URL", "http://test")
os.environ.setdefault("APP_ENV", "test")

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import ckac_common.database as db_module

db_module.engine = create_async_engine(
    os.environ["DATABASE_URL"],
    poolclass=NullPool,
    echo=False,
)
db_module.SessionLocal = async_sessionmaker(
    db_module.engine, class_=AsyncSession, expire_on_commit=False
)

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
        cur.execute("TRUNCATE TABLE ckac_orders.order_drafts CASCADE")
        cur.execute("TRUNCATE TABLE ckac_orders.order_status_events CASCADE")
        cur.execute("TRUNCATE TABLE ckac_orders.order_items CASCADE")
        cur.execute("TRUNCATE TABLE ckac_orders.orders CASCADE")
        cur.execute("TRUNCATE TABLE ckac_orders.master_orders CASCADE")
        cur.execute("TRUNCATE TABLE ckac_catalog.dish_media CASCADE")
        cur.execute("TRUNCATE TABLE ckac_catalog.dishes CASCADE")
        cur.execute("TRUNCATE TABLE ckac_catalog.categories CASCADE")
        cur.execute("TRUNCATE TABLE ckac_identity.kitchens CASCADE")
        cur.execute("TRUNCATE TABLE ckac_identity.customer_oauth_identities CASCADE")
        cur.execute("TRUNCATE TABLE ckac_identity.customers CASCADE")
        cur.execute("TRUNCATE TABLE ckac_identity.owners CASCADE")
        cur.execute("TRUNCATE TABLE ckac_events.outbox")
    conn.close()


async def _flush_order_stream() -> None:
    import redis.asyncio as redis

    client = redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
    try:
        await client.delete(
            "ckac:orders:order",
            "ckac:orders:draft",
            "ckac:orders:master_order",
        )
    finally:
        await client.aclose()


def _make_token(owner_id: uuid.UUID) -> str:
    expire = datetime.now(UTC) + timedelta(hours=1)
    return jwt.encode(
        {"sub": str(owner_id), "type": "owner", "exp": expire},
        JWT_SECRET,
        algorithm="HS256",
    )


def _seed_kitchen_with_dish() -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, str, str]:
    owner_id = uuid.uuid4()
    kitchen_id = uuid.uuid4()
    dish_id = uuid.uuid4()
    category_id = uuid.uuid4()
    phone = f"+91{owner_id.int % 9000000000 + 1000000000}"
    code = f"CKTST{owner_id.hex[:4].upper()}"
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ckac_identity.owners (id, phone, name, subscription_tier, subscription_status)
            VALUES (%s::uuid, %s, %s, 'starter', 'trial')
            """,
            (str(owner_id), phone, "Test Owner"),
        )
        cur.execute(
            """
            INSERT INTO ckac_identity.kitchens
            (id, owner_id, code, name, location, status)
            VALUES (
                %s::uuid, %s::uuid, %s, 'Test Kitchen',
                ST_SetSRID(ST_MakePoint(73.8958, 18.5362), 4326)::geography,
                'active'
            )
            """,
            (str(kitchen_id), str(owner_id), code),
        )
        cur.execute(
            """
            INSERT INTO ckac_catalog.categories (id, kitchen_id, name, slug, sort_order)
            VALUES (%s::uuid, %s::uuid, 'Veg', 'veg', 0)
            """,
            (str(category_id), str(kitchen_id)),
        )
        cur.execute(
            """
            INSERT INTO ckac_catalog.dishes
            (id, kitchen_id, category_id, name, price, prep_time_min, is_active)
            VALUES (%s::uuid, %s::uuid, %s::uuid, 'Paneer Tikka', 199.00, 25, true)
            """,
            (str(dish_id), str(kitchen_id), str(category_id)),
        )
    conn.close()
    return owner_id, kitchen_id, dish_id, code, _make_token(owner_id)


@pytest.fixture(autouse=True)
async def clean_db():
    _truncate_all()
    await _flush_order_stream()
    yield
    _truncate_all()
    await _flush_order_stream()


@pytest.fixture
async def client() -> AsyncClient:
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest.fixture
def order_ctx() -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, str, str]:
    return _seed_kitchen_with_dish()


MANUAL_ORDER_PAYLOAD = {
    "items": [{"dish_id": None, "quantity": 2}],
    "delivery_type": "pickup",
    "payment_method": "cod",
    "customer_name": "Walk-in Customer",
}


@pytest.fixture
def manual_order_payload(order_ctx) -> dict:
    _, _, dish_id, _, _ = order_ctx
    payload = MANUAL_ORDER_PAYLOAD.copy()
    payload["items"] = [{"dish_id": str(dish_id), "quantity": 2}]
    return payload
