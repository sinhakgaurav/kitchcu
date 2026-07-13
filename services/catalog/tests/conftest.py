"""Catalog service tests — TDD (Sprint 2)."""

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
        cur.execute("TRUNCATE TABLE ckac_catalog.dish_prep_steps CASCADE")
        cur.execute("TRUNCATE TABLE ckac_catalog.dish_ingredients CASCADE")
        cur.execute("TRUNCATE TABLE ckac_catalog.ingredients CASCADE")
        cur.execute("TRUNCATE TABLE ckac_catalog.dish_media CASCADE")
        cur.execute("TRUNCATE TABLE ckac_catalog.dishes CASCADE")
        cur.execute("TRUNCATE TABLE ckac_catalog.categories CASCADE")
        cur.execute("TRUNCATE TABLE ckac_catalog.cuisines CASCADE")
        cur.execute("TRUNCATE TABLE ckac_identity.kitchens CASCADE")
        cur.execute("TRUNCATE TABLE ckac_identity.owners CASCADE")
        cur.execute("TRUNCATE TABLE ckac_events.outbox")
    conn.close()


def _make_token(owner_id: uuid.UUID) -> str:
    expire = datetime.now(UTC) + timedelta(hours=1)
    return jwt.encode(
        {"sub": str(owner_id), "type": "owner", "exp": expire},
        JWT_SECRET,
        algorithm="HS256",
    )


def _seed_owner_kitchen() -> tuple[uuid.UUID, uuid.UUID, str]:
    owner_id = uuid.uuid4()
    kitchen_id = uuid.uuid4()
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
    conn.close()
    return owner_id, kitchen_id, _make_token(owner_id)


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


@pytest.fixture
def kitchen_ctx() -> tuple[uuid.UUID, uuid.UUID, str]:
    return _seed_owner_kitchen()


DISH_PAYLOAD_BASE = {
    "name": "Paneer Tikka",
    "price": 199.0,
    "prep_time_min": 25,
    "description": "Home-style paneer",
    "media": {
        "url": "https://minio/dish.jpg",
        "is_hero": True,
        "is_live_capture": True,
    },
}


async def build_dish_payload(client: AsyncClient, kitchen_id: uuid.UUID, token: str) -> dict:
    cuisines = (await client.get(f"/api/v1/kitchens/{kitchen_id}/cuisines")).json()
    cats = (
        await client.get(
            f"/api/v1/kitchens/{kitchen_id}/categories",
            headers={"Authorization": f"Bearer {token}"},
        )
    ).json()
    veg = next(c for c in cats if c["slug"] == "veg")
    return {
        **DISH_PAYLOAD_BASE,
        "cuisine_id": cuisines[0]["id"],
        "category_id": veg["id"],
    }


DISH_PAYLOAD = DISH_PAYLOAD_BASE  # legacy; tests should use build_dish_payload
