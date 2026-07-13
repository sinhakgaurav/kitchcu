from contextlib import asynccontextmanager

import httpx
import redis.asyncio as redis
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ckac_common.config import get_settings
from ckac_common.health import gateway_ready_response, live_response
from ckac_common.observability import CorrelationMiddleware, correlation_headers

settings = get_settings()
http_clients: dict[str, httpx.AsyncClient] = {}
redis_client: redis.Redis | None = None

IDENTITY_PREFIXES = ("/api/v1/auth", "/api/v1/owners", "/api/v1/admin", "/api/v1/customers")
CATALOG_PATH_MARKERS = ("/categories", "/menu", "/dishes", "/cuisines", "/ingredients", "/media")
ORDER_PATH_MARKERS = ("/orders", "/analytics")
MARKETING_PATH_MARKERS = ("/crm", "/coupons", "/promotions")
RATINGS_PATH_MARKERS = ("/ratings", "/suggestions")
GROWTH_PATH_MARKERS = ("/growth",)
LEARNING_PATH_MARKERS = ("/learning",)


def resolve_service_url(path: str) -> str | None:
    if path.startswith("/api/v1/customers/me/orders") and "/ratings" in path:
        return settings.ratings_service_url
    if path.startswith((
        "/api/v1/customers/me/orders",
        "/api/v1/customers/me/master-orders",
    )):
        return settings.order_service_url
    if any(path.startswith(p) for p in IDENTITY_PREFIXES):
        if path.startswith("/api/v1/admin/tickets"):
            return settings.notification_service_url
        return settings.identity_service_url
    if path.startswith("/api/v1/billing") or path.startswith("/api/v1/webhooks/razorpay"):
        return settings.billing_service_url
    if path.startswith("/api/v1/learning"):
        return settings.learning_service_url
    if path.startswith("/api/v1/growth"):
        return settings.growth_service_url
    if path.startswith("/api/v1/delivery"):
        return settings.delivery_service_url
    if path.startswith("/api/v1/marketing"):
        return settings.marketing_service_url
    if path.startswith("/api/v1/webhooks") or path.startswith("/api/v1/support"):
        return settings.notification_service_url
    if path.startswith("/api/v1/orders"):
        return settings.order_service_url
    if path.startswith("/api/v1/kitchens"):
        if any(marker in path for marker in LEARNING_PATH_MARKERS):
            return settings.learning_service_url
        if any(marker in path for marker in GROWTH_PATH_MARKERS):
            return settings.growth_service_url
        if any(marker in path for marker in RATINGS_PATH_MARKERS):
            return settings.ratings_service_url
        if any(marker in path for marker in ORDER_PATH_MARKERS):
            return settings.order_service_url
        if any(marker in path for marker in MARKETING_PATH_MARKERS):
            return settings.marketing_service_url
        if any(marker in path for marker in CATALOG_PATH_MARKERS):
            return settings.catalog_service_url
        return settings.identity_service_url
    return None


def resolve_client_key(base_url: str) -> str:
    if base_url == settings.catalog_service_url:
        return "catalog"
    if base_url == settings.order_service_url:
        return "order"
    if base_url == settings.billing_service_url:
        return "billing"
    if base_url == settings.notification_service_url:
        return "notification"
    if base_url == settings.marketing_service_url:
        return "marketing"
    if base_url == settings.ratings_service_url:
        return "ratings"
    if base_url == settings.growth_service_url:
        return "growth"
    if base_url == settings.delivery_service_url:
        return "delivery"
    if base_url == settings.learning_service_url:
        return "learning"
    return "identity"


@asynccontextmanager
async def lifespan(app: FastAPI):
    global http_clients, redis_client
    http_clients = {
        "identity": httpx.AsyncClient(base_url=settings.identity_service_url, timeout=30.0),
        "catalog": httpx.AsyncClient(base_url=settings.catalog_service_url, timeout=30.0),
        "order": httpx.AsyncClient(base_url=settings.order_service_url, timeout=30.0),
        "billing": httpx.AsyncClient(base_url=settings.billing_service_url, timeout=30.0),
        "notification": httpx.AsyncClient(base_url=settings.notification_service_url, timeout=30.0),
        "marketing": httpx.AsyncClient(base_url=settings.marketing_service_url, timeout=30.0),
        "ratings": httpx.AsyncClient(base_url=settings.ratings_service_url, timeout=30.0),
        "growth": httpx.AsyncClient(base_url=settings.growth_service_url, timeout=30.0),
        "delivery": httpx.AsyncClient(base_url=settings.delivery_service_url, timeout=30.0),
        "learning": httpx.AsyncClient(base_url=settings.learning_service_url, timeout=30.0),
    }
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    yield
    for client in http_clients.values():
        await client.aclose()
    http_clients.clear()
    if redis_client:
        await redis_client.aclose()


app = FastAPI(
    title="kitchCU API Gateway",
    version="0.4.0",
    description="Unified entry point — routes to identity, catalog, order, billing, marketing, ratings, growth, delivery, learning, notification",
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


@app.get("/health/live")
async def health_live() -> dict[str, str]:
    return live_response("gateway")


@app.get("/health/ready")
async def health_ready() -> dict:
    checks: dict[str, bool] = {}
    for name, client in http_clients.items():
        try:
            r = await client.get("/health/ready")
            checks[name] = r.status_code == 200
        except Exception:
            checks[name] = False
    redis_ok = False
    if redis_client:
        try:
            redis_ok = await redis_client.ping()
        except Exception:
            redis_ok = False
    return await gateway_ready_response("gateway", redis=redis_ok, services=checks)


@app.get("/")
async def root() -> dict[str, str]:
    return {"name": "kitchCU API Gateway", "version": "0.4.0", "docs": "/docs"}


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
async def proxy(path: str, request: Request) -> Response:
    full_path = f"/{path}"
    if request.method == "OPTIONS":
        return Response(status_code=204)
    base_url = resolve_service_url(full_path)
    if not base_url:
        return JSONResponse(status_code=404, content={"detail": "Route not found on gateway"})

    client_key = resolve_client_key(base_url)
    client = http_clients.get(client_key)
    if not client:
        return JSONResponse(status_code=503, content={"detail": "Gateway not ready"})

    url = full_path
    if request.url.query:
        url = f"{url}?{request.url.query}"

    body = await request.body()
    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in ("host", "content-length", "transfer-encoding")
    }
    headers.update(correlation_headers(request))

    upstream = await client.request(request.method, url, content=body, headers=headers)

    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers={
            k: v
            for k, v in upstream.headers.items()
            if k.lower() not in ("transfer-encoding", "content-encoding", "content-length")
        },
        media_type=upstream.headers.get("content-type"),
    )
