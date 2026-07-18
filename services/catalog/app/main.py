from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.internal_routes import router as internal_router
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
    title="kitchCU Catalog Service",
    version="0.1.0",
    description=(
        "Owns a kitchen's menu: cuisines, diet categories, dishes, and photo media. Enforces "
        "**truth in media** — active dish hero images must be live-captured, never stock photos. "
        "Also owns the ingredient balance mapper (F19): raw ingredient stock, dish recipes, "
        "low-stock warnings, and automatic stock deduction on order acceptance (via internal "
        "service-to-service routes called by the order service)."
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
app.include_router(internal_router, prefix="/api/v1")


@app.get("/health/live")
async def health_live() -> dict[str, str]:
    return live_response("catalog")


@app.get("/health/ready")
async def health_ready() -> dict:
    db_ok = await check_db_connection()
    redis_ok = False
    if redis_client:
        try:
            redis_ok = await redis_client.ping()
        except Exception:
            redis_ok = False
    return await ready_response("catalog", database=db_ok, redis=redis_ok)
