from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import router
from ckac_common.config import get_settings
from ckac_common.database import check_db_connection
from ckac_common.event_bus import EventPublisher
from ckac_common.events_context import set_event_publisher
from ckac_common.health import live_response, ready_response

settings = get_settings()
redis_client: redis.Redis | None = None
event_publisher = EventPublisher(None)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client, event_publisher
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    event_publisher = EventPublisher(redis_client)
    set_event_publisher(event_publisher)
    yield
    set_event_publisher(None)
    if redis_client:
        await redis_client.aclose()


app = FastAPI(
    title="kitchCU Learning Service",
    version="0.1.0",
    description=(
        "Helps owners grow their menu with confidence: a **curated recipe portal** (F21, public "
        "read) of vetted recipes owners can browse, and **dish trials** (F22, owner-only) — the "
        "workflow to turn a curated recipe into a draft dish, sample it with 5-20 CRM customers "
        "via WhatsApp, collect home-taste/quality ratings, and promote it to the live menu only "
        "once it clears a rating threshold (or is force-promoted by the owner). Trial dish/promote "
        "writes call the catalog service on the owner's behalf using their own Bearer token."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


@app.get("/health/live")
async def health_live() -> dict[str, str]:
    return live_response("learning")


@app.get("/health/ready")
async def health_ready() -> dict:
    db_ok = await check_db_connection()
    redis_ok = False
    if redis_client:
        try:
            redis_ok = await redis_client.ping()
        except Exception:
            redis_ok = False
    return await ready_response("learning", database=db_ok, redis=redis_ok)
