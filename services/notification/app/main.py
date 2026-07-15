from contextlib import asynccontextmanager

import httpx
import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.internal_routes import router as internal_router
from app.routes import router
from app.ticket_routes import admin_router as ticket_admin_router
from app.ticket_routes import public_router as ticket_public_router
from app.ticket_routes import customer_router as ticket_customer_router
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
    import app.routes as routes_module

    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    event_publisher = EventPublisher(redis_client)
    set_event_publisher(event_publisher)
    routes_module.redis_client = redis_client
    routes_module.event_publisher = event_publisher
    routes_module.http_client = httpx.AsyncClient(timeout=30.0)
    yield
    set_event_publisher(None)
    await routes_module.http_client.aclose()
    if redis_client:
        await redis_client.aclose()


app = FastAPI(
    title="kitchCU Notification Service",
    version="0.1.0",
    description=(
        "Owns all customer-facing messaging: **WhatsApp inbound** (Meta Cloud API webhook — "
        "verification + message parsing into draft orders), the **AI support assistant** "
        "(knowledge-base + optional LLM chat for the marketing site) and **support tickets** "
        "(public creation, platform-admin triage/reply), and **order/tracking dispatch** "
        "(F29/F45 — WhatsApp order-status updates and interval-based delivery tracking reminders, "
        "**internal-only**, called by the order/growth/learning services via `X-Internal-Key`). "
        "Never logs OTPs, tokens, or full phone numbers."
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
app.include_router(internal_router, prefix="/api/v1")
app.include_router(ticket_public_router, prefix="/api/v1")
app.include_router(ticket_admin_router, prefix="/api/v1")
app.include_router(ticket_customer_router, prefix="/api/v1")


@app.get("/health/live")
async def health_live() -> dict[str, str]:
    return live_response("notification")


@app.get("/health/ready")
async def health_ready() -> dict:
    db_ok = await check_db_connection()
    redis_ok = False
    if redis_client:
        try:
            redis_ok = await redis_client.ping()
        except Exception:
            redis_ok = False
    return await ready_response("notification", database=db_ok, redis=redis_ok)
