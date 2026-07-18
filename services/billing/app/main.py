from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import router
from app.admin_routes import router as admin_router
from app.internal_routes import router as internal_router
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
    title="kitchCU Billing Service",
    version="0.1.0",
    description=(
        "Owns money movement for kitchCU: order payments (owner + customer-initiated), UPI intents, "
        "Razorpay webhooks, multi-kitchen split settlements (Route), owner platform subscriptions, "
        "and GST compliance (profiles, tax invoices, monthly reports, balance sheet, audit close). "
        "kitchCU is an owner **subscription SaaS** with **zero per-order food commission** — "
        "`platform_fee` on settlements is always 0; the platform's only revenue is subscriptions."
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
app.include_router(admin_router, prefix="/api/v1")
app.include_router(internal_router, prefix="/api/v1")


@app.get("/health/live")
async def health_live() -> dict[str, str]:
    return live_response("billing")


@app.get("/health/ready")
async def health_ready() -> dict:
    db_ok = await check_db_connection()
    redis_ok = False
    if redis_client:
        try:
            redis_ok = await redis_client.ping()
        except Exception:
            redis_ok = False
    return await ready_response("billing", database=db_ok, redis=redis_ok)
