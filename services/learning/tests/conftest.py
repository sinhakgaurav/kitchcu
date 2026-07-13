"""Learning service tests — TDD (Sprint 16 F21–F22)."""

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
        cur.execute("TRUNCATE TABLE ckac_learning.trial_ratings CASCADE")
        cur.execute("TRUNCATE TABLE ckac_learning.trial_invites CASCADE")
        cur.execute("TRUNCATE TABLE ckac_learning.dish_trials CASCADE")
        cur.execute("TRUNCATE TABLE ckac_learning.curated_recipes CASCADE")
        cur.execute("TRUNCATE TABLE ckac_marketing.kitchen_customers CASCADE")
        cur.execute("TRUNCATE TABLE ckac_identity.customers CASCADE")
        cur.execute("TRUNCATE TABLE ckac_identity.kitchens CASCADE")
        cur.execute("TRUNCATE TABLE ckac_identity.owners CASCADE")
        cur.execute("TRUNCATE TABLE ckac_events.outbox")
    conn.close()


async def _flush_learning_streams() -> None:
    import redis.asyncio as redis

    client = redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
    try:
        await client.delete("ckac:learning:trial")
    finally:
        await client.aclose()


def _make_owner_token(owner_id: uuid.UUID) -> str:
    expire = datetime.now(UTC) + timedelta(hours=1)
    return jwt.encode(
        {"sub": str(owner_id), "type": "owner", "exp": expire},
        JWT_SECRET,
        algorithm="HS256",
    )


def _seed_learning_ctx() -> dict:
    owner_id = uuid.uuid4()
    kitchen_id = uuid.uuid4()
    recipe_id = uuid.uuid4()
    trial_dish_id = uuid.uuid4()
    phone = f"+919{owner_id.int % 900000000 + 100000000}"
    code = f"CKL{owner_id.hex[:4].upper()}"
    customer_ids = [uuid.uuid4() for _ in range(6)]

    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ckac_identity.owners (id, phone, name, subscription_tier, subscription_status)
            VALUES (%s::uuid, %s, 'Learning Owner', 'starter', 'trial')
            """,
            (str(owner_id), phone),
        )
        cur.execute(
            """
            INSERT INTO ckac_identity.kitchens
            (id, owner_id, code, name, location, status)
            VALUES (
                %s::uuid, %s::uuid, %s, 'Learning Kitchen',
                ST_SetSRID(ST_MakePoint(73.8958, 18.5362), 4326)::geography,
                'active'
            )
            """,
            (str(kitchen_id), str(owner_id), code),
        )
        cur.execute(
            """
            INSERT INTO ckac_learning.curated_recipes
            (id, title, slug, category, cuisine, description, ingredients, prep_steps,
             image_url, source_name, is_active)
            VALUES (
                %s::uuid, 'Test Korma', 'test-korma', 'north_indian', 'north_indian',
                'Creamy nut-based curry for trials.',
                '["paneer","cashew"]', '["Simmer gravy"]',
                'https://example.com/korma.jpg', 'kitchCU Test', true
            )
            """,
            (str(recipe_id),),
        )
        for i, cid in enumerate(customer_ids):
            cphone = f"+919{cid.int % 900000000 + 100000000}"
            cur.execute(
                """
                INSERT INTO ckac_identity.customers (id, phone, name, status)
                VALUES (%s::uuid, %s, %s, 'active')
                """,
                (str(cid), cphone, f"Trial Customer {i + 1}"),
            )
            cur.execute(
                """
                INSERT INTO ckac_marketing.kitchen_customers
                (id, kitchen_id, customer_id, customer_phone, customer_name, order_count)
                VALUES (%s::uuid, %s::uuid, %s::uuid, %s, %s, 2)
                """,
                (str(uuid.uuid4()), str(kitchen_id), str(cid), cphone, f"Trial Customer {i + 1}"),
            )
    conn.close()

    return {
        "owner_id": owner_id,
        "kitchen_id": kitchen_id,
        "recipe_id": recipe_id,
        "trial_dish_id": trial_dish_id,
        "customer_ids": customer_ids,
        "owner_token": _make_owner_token(owner_id),
    }


@pytest.fixture(autouse=True)
async def clean_db():
    _truncate_all()
    await _flush_learning_streams()
    yield
    _truncate_all()
    await _flush_learning_streams()


@pytest.fixture
async def client() -> AsyncClient:
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest.fixture
def learning_ctx() -> dict:
    return _seed_learning_ctx()
