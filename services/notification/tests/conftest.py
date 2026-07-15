"""Notification service test fixtures."""

import os
from datetime import UTC, datetime, timedelta

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
os.environ.setdefault("WHATSAPP_VERIFY_TOKEN", "ckac-dev-verify")
os.environ.setdefault("ORDER_SERVICE_URL", "http://test")
os.environ.setdefault("INTERNAL_API_KEY", "test-internal-key-for-pytest")
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

import psycopg2
import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from jose import jwt

from app.main import app
from tests.events_bootstrap import ensure_events_schema

SYNC_DB_URL = os.environ["DATABASE_SYNC_URL"]
JWT_SECRET = os.environ["JWT_SECRET"]
WEBHOOK_PAYLOAD = {
    "entry": [
        {
            "changes": [
                {
                    "value": {
                        "metadata": {"phone_number_id": "PHONE123"},
                        "messages": [
                            {
                                "id": "wamid.test",
                                "from": "919876543210",
                                "type": "text",
                                "text": {"body": "2 Paneer Tikka"},
                            }
                        ],
                    }
                }
            ]
        }
    ]
}


def _seed_platform_admin() -> None:
    admin_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS ckac_support")
        cur.execute(
            """
            INSERT INTO ckac_identity.platform_admins (id, email, password_hash, name, role, is_active)
            VALUES (%s::uuid, 'admin@test.ckac', 'hash', 'Test Admin', 'superadmin', true)
            ON CONFLICT (email) DO NOTHING
            """,
            (admin_id,),
        )
    conn.close()


def _admin_token() -> str:
    expire = datetime.now(UTC) + timedelta(hours=1)
    return jwt.encode(
        {
            "sub": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "email": "admin@test.ckac",
            "type": "admin",
            "exp": expire,
        },
        JWT_SECRET,
        algorithm="HS256",
    )


def _truncate_all() -> None:
    ensure_events_schema(SYNC_DB_URL)
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS ckac_support")
        cur.execute("CREATE SCHEMA IF NOT EXISTS ckac_notifications")
        cur.execute("TRUNCATE TABLE ckac_notifications.tracking_reminders CASCADE")
        cur.execute("TRUNCATE TABLE ckac_notifications.notification_log CASCADE")
        cur.execute("TRUNCATE TABLE ckac_support.support_ticket_messages CASCADE")
        cur.execute("TRUNCATE TABLE ckac_support.support_tickets CASCADE")
        cur.execute("TRUNCATE TABLE ckac_orders.order_drafts CASCADE")
        cur.execute("TRUNCATE TABLE ckac_orders.order_items CASCADE")
        cur.execute("TRUNCATE TABLE ckac_orders.orders CASCADE")
        cur.execute("TRUNCATE TABLE ckac_catalog.dishes CASCADE")
        cur.execute("TRUNCATE TABLE ckac_catalog.categories CASCADE")
        cur.execute("TRUNCATE TABLE ckac_identity.kitchens CASCADE")
        cur.execute("TRUNCATE TABLE ckac_identity.owners CASCADE")
        cur.execute("TRUNCATE TABLE ckac_events.outbox")
    conn.close()


def _seed_kitchen(whatsapp_phone_id: str = "PHONE123") -> uuid.UUID:
    owner_id = uuid.uuid4()
    kitchen_id = uuid.uuid4()
    category_id = uuid.uuid4()
    dish_id = uuid.uuid4()
    phone = f"+91{owner_id.int % 9000000000 + 1000000000}"
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO ckac_identity.owners (id, phone, name, subscription_tier, subscription_status) "
            "VALUES (%s::uuid, %s, 'T', 'starter', 'trial')",
            (str(owner_id), phone),
        )
        cur.execute(
            """
            INSERT INTO ckac_identity.kitchens
            (id, owner_id, code, name, location, status, whatsapp_phone_id)
            VALUES (%s::uuid, %s::uuid, %s, 'K', ST_SetSRID(ST_MakePoint(73.8, 18.5), 4326)::geography,
                    'active', %s)
            """,
            (str(kitchen_id), str(owner_id), f"CK{owner_id.hex[:4].upper()}", whatsapp_phone_id),
        )
        cur.execute(
            "INSERT INTO ckac_catalog.categories (id, kitchen_id, name, slug, sort_order) "
            "VALUES (%s::uuid, %s::uuid, 'Veg', 'veg', 0)",
            (str(category_id), str(kitchen_id)),
        )
        cur.execute(
            "INSERT INTO ckac_catalog.dishes (id, kitchen_id, category_id, name, price, prep_time_min, delivery_time_min, max_time_min, is_active) "
            "VALUES (%s::uuid, %s::uuid, %s::uuid, 'Paneer Tikka', 199, 25, 20, 45, true)",
            (str(dish_id), str(kitchen_id), str(category_id)),
        )
    conn.close()
    return kitchen_id


@pytest.fixture(autouse=True)
def clean_db():
    _truncate_all()
    yield
    _truncate_all()


@pytest.fixture
async def client() -> AsyncClient:
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
