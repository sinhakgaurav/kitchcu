"""Growth service tests — TDD (Sprint 12)."""

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
        cur.execute("TRUNCATE TABLE ckac_growth.suggestions CASCADE")
        cur.execute("TRUNCATE TABLE ckac_growth.seasonal_patterns CASCADE")
        cur.execute("TRUNCATE TABLE ckac_marketing.kitchen_customers CASCADE")
        cur.execute("TRUNCATE TABLE ckac_ratings.dish_rating_aggregates CASCADE")
        cur.execute("TRUNCATE TABLE ckac_orders.order_items CASCADE")
        cur.execute("TRUNCATE TABLE ckac_orders.order_status_events CASCADE")
        cur.execute("TRUNCATE TABLE ckac_orders.orders CASCADE")
        cur.execute("TRUNCATE TABLE ckac_catalog.dish_media CASCADE")
        cur.execute("TRUNCATE TABLE ckac_catalog.dishes CASCADE")
        cur.execute("TRUNCATE TABLE ckac_catalog.categories CASCADE")
        cur.execute("TRUNCATE TABLE ckac_identity.customers CASCADE")
        cur.execute("TRUNCATE TABLE ckac_identity.kitchens CASCADE")
        cur.execute("TRUNCATE TABLE ckac_identity.owners CASCADE")
        cur.execute("TRUNCATE TABLE ckac_events.outbox")
    conn.close()


async def _flush_growth_streams() -> None:
    import redis.asyncio as redis

    client = redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
    try:
        await client.delete("ckac:growth:suggestion", "ckac:growth:daily_menu")
    finally:
        await client.aclose()


def _make_owner_token(owner_id: uuid.UUID) -> str:
    expire = datetime.now(UTC) + timedelta(hours=1)
    return jwt.encode(
        {"sub": str(owner_id), "type": "owner", "exp": expire},
        JWT_SECRET,
        algorithm="HS256",
    )


def _seed_growth_ctx() -> dict:
    owner_id = uuid.uuid4()
    kitchen_id = uuid.uuid4()
    customer_id = uuid.uuid4()
    dish_a = uuid.uuid4()
    dish_b = uuid.uuid4()
    dish_c = uuid.uuid4()
    category_id = uuid.uuid4()
    phone = f"+919{owner_id.int % 900000000 + 100000000}"
    customer_phone = f"+919{customer_id.int % 900000000 + 100000000}"
    code = f"CKG{owner_id.hex[:4].upper()}"
    now = datetime.now(UTC)

    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ckac_identity.owners (id, phone, name, subscription_tier, subscription_status)
            VALUES (%s::uuid, %s, %s, 'starter', 'trial')
            """,
            (str(owner_id), phone, "Growth Owner"),
        )
        cur.execute(
            """
            INSERT INTO ckac_identity.kitchens
            (id, owner_id, code, name, location, status)
            VALUES (
                %s::uuid, %s::uuid, %s, 'Growth Kitchen',
                ST_SetSRID(ST_MakePoint(73.8958, 18.5362), 4326)::geography,
                'active'
            )
            """,
            (str(kitchen_id), str(owner_id), code),
        )
        cur.execute(
            """
            INSERT INTO ckac_identity.customers (id, phone, name, status)
            VALUES (%s::uuid, %s, 'Growth Customer', 'active')
            """,
            (str(customer_id), customer_phone),
        )
        cur.execute(
            """
            INSERT INTO ckac_catalog.categories (id, kitchen_id, name, slug, sort_order)
            VALUES (%s::uuid, %s::uuid, 'Veg', 'veg', 1)
            """,
            (str(category_id), str(kitchen_id)),
        )
        for did, name, price in [
            (dish_a, "Butter Naan", 49.0),
            (dish_b, "Dal Makhani", 149.0),
            (dish_c, "Paneer Tikka", 199.0),
        ]:
            cur.execute(
                """
                INSERT INTO ckac_catalog.dishes
                (id, kitchen_id, category_id, name, price, prep_time_min, is_active)
                VALUES (%s::uuid, %s::uuid, %s::uuid, %s, %s, 20, true)
                """,
                (str(did), str(kitchen_id), str(category_id), name, price),
            )

        cur.execute(
            """
            INSERT INTO ckac_ratings.dish_rating_aggregates
            (id, kitchen_id, dish_id, rating_count, avg_home_taste, avg_quality, overall_rating)
            VALUES (%s::uuid, %s::uuid, %s::uuid, 5, 4.8, 4.6, 4.7)
            """,
            (str(uuid.uuid4()), str(kitchen_id), str(dish_c)),
        )

        cur.execute(
            """
            INSERT INTO ckac_marketing.kitchen_customers
            (id, kitchen_id, customer_id, customer_phone, customer_name, order_count)
            VALUES (%s::uuid, %s::uuid, %s::uuid, %s, 'Growth Customer', 3)
            """,
            (str(uuid.uuid4()), str(kitchen_id), str(customer_id), customer_phone),
        )

        for i in range(4):
            order_id = uuid.uuid4()
            created = now - timedelta(days=i, hours=12)
            cur.execute(
                """
                INSERT INTO ckac_orders.orders
                (id, kitchen_id, bill_id, order_code, status, source, delivery_type,
                 payment_method, customer_phone, customer_name, subtotal, delivery_fee, total, created_at)
                VALUES (
                    %s::uuid, %s::uuid, %s, %s, 'delivered', 'pwa',
                    'delivery', 'cod', %s, 'Growth Customer', 198.00, 0, 198.00, %s
                )
                """,
                (
                    str(order_id),
                    str(kitchen_id),
                    f"BILL-2026071{i}-010{i}",
                    f"{code}-BILL-2026071{i}-010{i}",
                    customer_phone,
                    created,
                ),
            )
            for did, name, price in [(dish_a, "Butter Naan", 49.0), (dish_b, "Dal Makhani", 149.0)]:
                cur.execute(
                    """
                    INSERT INTO ckac_orders.order_items
                    (id, order_id, dish_id, dish_name, quantity, unit_price)
                    VALUES (%s::uuid, %s::uuid, %s::uuid, %s, 1, %s)
                    """,
                    (str(uuid.uuid4()), str(order_id), str(did), name, price),
                )

        old_order_id = uuid.uuid4()
        old_created = now - timedelta(days=30)
        cur.execute(
            """
            INSERT INTO ckac_orders.orders
            (id, kitchen_id, bill_id, order_code, status, source, delivery_type,
             payment_method, customer_phone, customer_name, subtotal, delivery_fee, total, created_at)
            VALUES (
                %s::uuid, %s::uuid, 'BILL-OLD-0100', %s, 'delivered', 'pwa',
                'delivery', 'cod', %s, 'Churn Customer', 149.00, 0, 149.00, %s
            )
            """,
            (
                str(old_order_id),
                str(kitchen_id),
                f"{code}-BILL-OLD-0100",
                f"+919{uuid.uuid4().int % 900000000 + 100000000}",
                old_created,
            ),
        )
        cur.execute(
            """
            INSERT INTO ckac_orders.orders
            (id, kitchen_id, bill_id, order_code, status, source, delivery_type,
             payment_method, customer_phone, customer_name, subtotal, delivery_fee, total, created_at)
            VALUES (
                %s::uuid, %s::uuid, 'BILL-OLD-0101', %s, 'delivered', 'pwa',
                'delivery', 'cod', %s, 'Churn Customer', 149.00, 0, 149.00, %s
            )
            """,
            (
                str(uuid.uuid4()),
                str(kitchen_id),
                f"{code}-BILL-OLD-0101",
                f"+919{uuid.uuid4().int % 900000000 + 100000000}",
                old_created - timedelta(days=5),
            ),
        )

        cur.execute(
            """
            INSERT INTO ckac_growth.seasonal_patterns
            (id, region, season_event, dish_category, demand_multiplier, sample_dishes)
            VALUES (%s::uuid, 'india', 'diwali', 'seasonal_special', 1.45, '["Gulab Jamun"]')
            """,
            (str(uuid.uuid4()),),
        )

    conn.close()

    return {
        "owner_id": owner_id,
        "kitchen_id": kitchen_id,
        "customer_id": customer_id,
        "dish_a": dish_a,
        "dish_b": dish_b,
        "dish_c": dish_c,
        "owner_token": _make_owner_token(owner_id),
    }


@pytest.fixture(autouse=True)
async def clean_db():
    _truncate_all()
    await _flush_growth_streams()
    yield
    _truncate_all()
    await _flush_growth_streams()


@pytest.fixture
async def client() -> AsyncClient:
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest.fixture
def growth_ctx() -> dict:
    return _seed_growth_ctx()
