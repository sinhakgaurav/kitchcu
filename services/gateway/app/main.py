import asyncio
from contextlib import asynccontextmanager

import httpx
import redis.asyncio as redis
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import JSONResponse

from app.openapi_aggregate import build_gateway_openapi
from app.rate_limit import check_rate_limit
from ckac_common.config import get_settings
from ckac_common.health import gateway_ready_response, live_response
from ckac_common.observability import CorrelationMiddleware, correlation_headers

settings = get_settings()
http_clients: dict[str, httpx.AsyncClient] = {}
redis_client: redis.Redis | None = None
_openapi_cache: dict | None = None

IDENTITY_PREFIXES = ("/api/v1/auth", "/api/v1/owners", "/api/v1/admin", "/api/v1/customers")
CATALOG_PATH_MARKERS = ("/categories", "/menu", "/dishes", "/cuisines", "/ingredients", "/media")
ORDER_PATH_MARKERS = ("/orders", "/analytics")
MARKETING_PATH_MARKERS = ("/crm", "/coupons", "/promotions")
GST_PATH_MARKERS = ("/gst",)
RATINGS_PATH_MARKERS = ("/ratings", "/suggestions")
GROWTH_PATH_MARKERS = ("/growth",)
LEARNING_PATH_MARKERS = ("/learning",)
COMMUNITY_PATH_MARKERS = ("/community",)
STREAMING_PATH_MARKERS = ("/stream",)
GATEWAY_OWNED_PATHS = {
    "/",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/health/live",
    "/health/ready",
}


def resolve_service_url(path: str) -> str | None:
    if path.startswith("/api/v1/customers/me/orders") and "/ratings" in path:
        return settings.ratings_service_url
    if path.startswith("/api/v1/customers/me/dashboard"):
        return settings.order_service_url
    if path.startswith("/api/v1/customers/me/tickets"):
        return settings.notification_service_url
    if path.startswith((
        "/api/v1/customers/me/orders",
        "/api/v1/customers/me/master-orders",
    )):
        return settings.order_service_url
    if path.startswith((
        "/api/v1/admin/refunds",
        "/api/v1/admin/payments",
        "/api/v1/admin/settlements",
        "/api/v1/admin/money-stats",
    )):
        return settings.billing_service_url
    if any(path.startswith(p) for p in IDENTITY_PREFIXES):
        if path.startswith("/api/v1/admin/tickets"):
            return settings.notification_service_url
        return settings.identity_service_url
    if path.startswith("/api/v1/billing") or path.startswith("/api/v1/webhooks/razorpay"):
        return settings.billing_service_url
    if path.startswith("/api/v1/community"):
        return settings.community_service_url
    if path.startswith("/api/v1/stream"):
        return settings.streaming_service_url
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
        if any(marker in path for marker in STREAMING_PATH_MARKERS):
            return settings.streaming_service_url
        if any(marker in path for marker in COMMUNITY_PATH_MARKERS):
            return settings.community_service_url
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
        if any(marker in path for marker in GST_PATH_MARKERS):
            return settings.billing_service_url
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
    if base_url == settings.community_service_url:
        return "community"
    if base_url == settings.streaming_service_url:
        return "streaming"
    return "identity"


@asynccontextmanager
async def lifespan(app: FastAPI):
    global http_clients, redis_client, _openapi_cache
    http_clients = {
        "identity": httpx.AsyncClient(base_url=settings.identity_service_url, timeout=httpx.Timeout(10.0, connect=5.0)),
        "catalog": httpx.AsyncClient(base_url=settings.catalog_service_url, timeout=httpx.Timeout(10.0, connect=5.0)),
        "order": httpx.AsyncClient(base_url=settings.order_service_url, timeout=httpx.Timeout(30.0, connect=5.0)),
        "billing": httpx.AsyncClient(base_url=settings.billing_service_url, timeout=httpx.Timeout(10.0, connect=5.0)),
        "notification": httpx.AsyncClient(base_url=settings.notification_service_url, timeout=httpx.Timeout(10.0, connect=5.0)),
        "marketing": httpx.AsyncClient(base_url=settings.marketing_service_url, timeout=httpx.Timeout(10.0, connect=5.0)),
        "ratings": httpx.AsyncClient(base_url=settings.ratings_service_url, timeout=httpx.Timeout(10.0, connect=5.0)),
        "growth": httpx.AsyncClient(base_url=settings.growth_service_url, timeout=httpx.Timeout(10.0, connect=5.0)),
        "delivery": httpx.AsyncClient(base_url=settings.delivery_service_url, timeout=httpx.Timeout(10.0, connect=5.0)),
        "learning": httpx.AsyncClient(base_url=settings.learning_service_url, timeout=httpx.Timeout(10.0, connect=5.0)),
        "community": httpx.AsyncClient(base_url=settings.community_service_url, timeout=httpx.Timeout(10.0, connect=5.0)),
        "streaming": httpx.AsyncClient(base_url=settings.streaming_service_url, timeout=httpx.Timeout(10.0, connect=5.0)),
    }
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    _openapi_cache = None
    yield
    for client in http_clients.values():
        await client.aclose()
    http_clients.clear()
    if redis_client:
        await redis_client.aclose()
    _openapi_cache = None


app = FastAPI(
    title="kitchCU API Gateway",
    version="1.0.0",
    description=(
        "Unified public edge for /api/v1/* — aggregates OpenAPI from all domain services. "
        "Explore the full contract at /docs or the portal OpenAPI page."
    ),
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
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
    # Probe /health/live in parallel with a short timeout. Cascading each
    # upstream's /health/ready (DB+Redis) sequentially can hang the gateway for minutes.
    async def _probe(name: str, client: httpx.AsyncClient) -> tuple[str, bool]:
        try:
            r = await client.get("/health/live", timeout=2.0)
            return name, r.status_code == 200
        except Exception:
            return name, False

    results = await asyncio.gather(*(_probe(n, c) for n, c in http_clients.items()))
    checks = dict(results)
    redis_ok = False
    if redis_client:
        try:
            redis_ok = bool(await asyncio.wait_for(redis_client.ping(), timeout=2.0))
        except Exception:
            redis_ok = False
    return await gateway_ready_response("gateway", redis=redis_ok, services=checks)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "name": "kitchCU API Gateway",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "openapi": "/openapi.json",
        "api_prefix": "/api/v1",
    }


@app.get("/openapi.json", include_in_schema=False)
async def openapi_json(request: Request, refresh: bool = False) -> JSONResponse:
    """Aggregated OpenAPI from all upstream domain services."""
    global _openapi_cache
    if refresh or _openapi_cache is None:
        _openapi_cache = await build_gateway_openapi(
            http_clients,
            servers=[
                {
                    "url": str(request.base_url).rstrip("/"),
                    "description": "API Gateway",
                }
            ],
        )
    return JSONResponse(_openapi_cache)


@app.get("/docs", include_in_schema=False)
async def swagger_ui() -> Response:
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="kitchCU API — OpenAPI",
        swagger_ui_parameters={"persistAuthorization": True},
    )


@app.get("/redoc", include_in_schema=False)
async def redoc_ui() -> Response:
    return get_redoc_html(openapi_url="/openapi.json", title="kitchCU API — ReDoc")


@app.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
    include_in_schema=False,
)
async def proxy(path: str, request: Request) -> Response:
    full_path = f"/{path}"
    if full_path in GATEWAY_OWNED_PATHS or full_path.startswith("/docs/") or full_path.startswith("/redoc/"):
        return JSONResponse(status_code=404, content={"detail": "Not found"})
    if request.method == "OPTIONS":
        return Response(status_code=204)

    allowed, retry_after, _rule_name = await check_rate_limit(redis_client, request, full_path)
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"detail": f"Too many requests — try again in {retry_after}s"},
            headers={"Retry-After": str(retry_after)},
        )

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

    try:
        upstream = await client.request(request.method, url, content=body, headers=headers)
    except httpx.ConnectError:
        return JSONResponse(
            status_code=503,
            content={"detail": "Backend service unavailable — ensure Docker stack is running"},
        )
    except httpx.TimeoutException:
        return JSONResponse(
            status_code=504,
            content={"detail": "Backend service timed out — try again or restart Docker"},
        )
    except httpx.HTTPError as exc:
        return JSONResponse(status_code=502, content={"detail": f"Gateway upstream error: {exc}"})

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
