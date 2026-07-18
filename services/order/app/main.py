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
from ckac_common.observability import CorrelationMiddleware

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
    title="kitchCU Order Service",
    version="0.1.0",
    description=(
        "Order lifecycle for cloud kitchens — the system of record for every order placed "
        "against a kitchen, whether entered by the owner, checked out by a customer, or "
        "parsed from WhatsApp.\n\n"
        "**Surface areas**\n"
        "- **Owner Orders** — manual order entry, WhatsApp/pasted-message parsing into review "
        "drafts, draft confirmation, order listing, status lifecycle transitions, and "
        "ingredient stock-shortfall warnings (F19).\n"
        "- **Customer Checkout** — single-kitchen cart checkout, order history (F33), repeat "
        "order.\n"
        "- **Master Orders** — multi-kitchen checkout (F06): one payment, idempotent creation, "
        "grouped into per-kitchen sub-orders with an aggregated receipt (F44 split settlement "
        "happens downstream in billing).\n"
        "- **Analytics** — owner revenue summary/timeseries, top dishes, peak hours, and "
        "customer segments (F07-F08).\n"
        "- **Bills** — PDF receipt generation for orders and master orders.\n\n"
        "**Status machine:** `received -> accepted -> preparing -> ready -> out_for_delivery "
        "-> delivered`, with `cancelled` reachable from any non-terminal status; `delivered` "
        "and `cancelled` are terminal.\n\n"
        "**Order sources:** `manual` (owner-keyed), `customer_app`/`customer_pwa` (customer "
        "checkout), `customer_pwa_multi` (master order sub-order), `whatsapp` (parsed inbound "
        "message), `manual_message` (parsed pasted message).\n\n"
        "**Pricing:** every order's `total` is always `subtotal + delivery_fee`, computed "
        "server-side from live catalog prices and kitchen delivery-radius rules.\n\n"
        "**Auth:** Owner JWT (Bearer) on owner routes, Customer JWT (Bearer) on checkout/"
        "history routes, `X-Internal-Key` on service-to-service intake routes."
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
app.add_middleware(CorrelationMiddleware)

app.include_router(router, prefix="/api/v1")


@app.get("/health/live")
async def health_live() -> dict[str, str]:
    return live_response("order")


@app.get("/health/ready")
async def health_ready() -> dict:
    db_ok = await check_db_connection()
    redis_ok = False
    if redis_client:
        try:
            redis_ok = await redis_client.ping()
        except Exception:
            redis_ok = False
    return await ready_response("order", database=db_ok, redis=redis_ok)
