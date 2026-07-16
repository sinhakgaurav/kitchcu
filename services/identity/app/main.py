from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.admin_routes import router as admin_router
from app.customer_routes import router as customer_router
from app.internal_routes import router as internal_router
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
    title="kitchCU Identity Service",
    version="0.2.0",
    description=(
        "Owner registration, kitchen onboarding, customer OAuth/WhatsApp login, and platform "
        "admin authentication for kitchCU.\n\n"
        "Endpoints are grouped by tag — **Auth** (owner OTP), **Owners**, **Kitchens**, "
        "**Discovery** (public nearby/by-code search), **Customer Auth** (OAuth + WhatsApp OTP), "
        "and **Admin** (platform moderation).\n\n"
        "Every request/response model documents its fields with `description` + `examples`, "
        "and every route documents `summary`, auth requirements, and the error `responses` it "
        "can return — see the schema definitions below for exact JWT payload shapes "
        "(`type=owner` / `type=customer` / `type=admin`)."
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
app.include_router(customer_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(internal_router, prefix="/api/v1")


@app.get("/health/live")
async def health_live() -> dict[str, str]:
    return live_response("identity")


@app.get("/health/ready")
async def health_ready() -> dict:
    db_ok = await check_db_connection()
    redis_ok = False
    if redis_client:
        try:
            redis_ok = await redis_client.ping()
        except Exception:
            redis_ok = False
    return await ready_response("identity", database=db_ok, redis=redis_ok)
