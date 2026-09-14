import os

os.environ.setdefault("REDIS_URL", "redis://localhost:16379/0")
os.environ.setdefault("IDENTITY_SERVICE_URL", "http://identity:8001")
os.environ.setdefault("CATALOG_SERVICE_URL", "http://catalog:8002")
os.environ.setdefault("ORDER_SERVICE_URL", "http://order:8003")
os.environ.setdefault("BILLING_SERVICE_URL", "http://billing:8004")
os.environ.setdefault("NOTIFICATION_SERVICE_URL", "http://notification:8005")
os.environ.setdefault("MARKETING_SERVICE_URL", "http://marketing:8006")
os.environ.setdefault("RATINGS_SERVICE_URL", "http://ratings:8007")
os.environ.setdefault("GROWTH_SERVICE_URL", "http://growth:8008")
os.environ.setdefault("DELIVERY_SERVICE_URL", "http://delivery:8009")

from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient, Response

from app import main as gateway_main
from starlette.requests import Request

from app.main import app, resolve_service_url
from app.openapi_aggregate import SAME_ORIGIN_SERVERS, public_gateway_servers


@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.ping = AsyncMock(return_value=True)
    redis.aclose = AsyncMock()
    return redis


@pytest.fixture
def mock_clients():
    identity = AsyncMock()
    catalog = AsyncMock()
    order = AsyncMock()
    billing = AsyncMock()
    notification = AsyncMock()
    marketing = AsyncMock()
    ratings = AsyncMock()
    growth = AsyncMock()
    delivery = AsyncMock()
    return {"identity": identity, "catalog": catalog, "order": order, "billing": billing, "notification": notification, "marketing": marketing, "ratings": ratings, "growth": growth, "delivery": delivery}


@pytest.fixture
async def gateway_client(mock_redis, mock_clients):
    gateway_main.redis_client = mock_redis
    gateway_main.http_clients = mock_clients
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, mock_clients
    gateway_main.redis_client = None
    gateway_main.http_clients = {}


def test_resolve_service_url_identity():
    assert resolve_service_url("/api/v1/auth/otp/request") is not None
    assert resolve_service_url("/api/v1/owners/register") is not None
    assert resolve_service_url("/api/v1/kitchens") is not None


def test_resolve_service_url_catalog():
    from ckac_common.config import get_settings

    settings = get_settings()
    url = resolve_service_url("/api/v1/kitchens/abc/menu")
    assert url == settings.catalog_service_url
    assert resolve_service_url("/api/v1/kitchens/abc/dishes") == settings.catalog_service_url
    assert resolve_service_url("/api/v1/kitchens/abc/prep-batches") == settings.catalog_service_url
    assert resolve_service_url("/api/v1/kitchens/abc/stock-settings") == settings.catalog_service_url
    assert resolve_service_url("/api/v1/kitchens/me") == settings.identity_service_url
    assert resolve_service_url("/api/v1/kitchens/abc/profile") == settings.identity_service_url
    assert resolve_service_url("/api/v1/admin/kitchens/abc/profile") == settings.identity_service_url
    assert resolve_service_url("/api/v1/admin/kitchens/abc/orders/export.csv") == settings.identity_service_url
    assert resolve_service_url("/api/v1/admin/kitchens/abc/orders/parse-stats") == settings.identity_service_url


def test_resolve_service_url_order():
    from ckac_common.config import get_settings

    settings = get_settings()
    assert resolve_service_url("/api/v1/orders/abc-uuid") == settings.order_service_url
    assert (
        resolve_service_url("/api/v1/kitchens/abc/orders/manual") == settings.order_service_url
    )
    assert (
        resolve_service_url("/api/v1/kitchens/abc/analytics/summary")
        == settings.order_service_url
    )
    assert (
        resolve_service_url("/api/v1/kitchens/abc/analytics/customers")
        == settings.order_service_url
    )
    assert (
        resolve_service_url("/api/v1/kitchens/abc/orders/export.csv")
        == settings.order_service_url
    )
    assert (
        resolve_service_url("/api/v1/kitchens/abc/orders/drafts/parse-stats")
        == settings.order_service_url
    )


def test_resolve_service_url_customer_dashboard_and_tickets():
    from app.main import resolve_service_url
    from ckac_common.config import get_settings

    settings = get_settings()
    assert resolve_service_url("/api/v1/customers/me/dashboard") == settings.order_service_url
    assert resolve_service_url("/api/v1/customers/me/tickets") == settings.notification_service_url
    assert resolve_service_url("/api/v1/customers/me/addresses") == settings.identity_service_url
    assert resolve_service_url("/api/v1/customers/me/orders") == settings.order_service_url
    assert (
        resolve_service_url("/api/v1/customers/me/master-orders")
        == settings.order_service_url
    )


def test_resolve_service_url_billing():
    from ckac_common.config import get_settings

    settings = get_settings()
    assert resolve_service_url("/api/v1/billing/payments") == settings.billing_service_url
    assert resolve_service_url("/api/v1/billing/subscriptions/plans") == settings.billing_service_url
    assert resolve_service_url("/api/v1/webhooks/razorpay") == settings.billing_service_url
    assert resolve_service_url("/api/v1/admin/refunds") == settings.billing_service_url
    assert resolve_service_url("/api/v1/admin/payments") == settings.billing_service_url
    assert resolve_service_url("/api/v1/admin/settlements") == settings.billing_service_url
    assert resolve_service_url("/api/v1/admin/money-stats") == settings.billing_service_url
    assert (
        resolve_service_url("/api/v1/admin/kitchens/abc/payment-gateway")
        == settings.billing_service_url
    )
    assert resolve_service_url("/api/v1/admin/kitchens/abc") == settings.identity_service_url
    assert (
        resolve_service_url("/api/v1/admin/kitchens/abc/whatsapp-integration")
        == settings.identity_service_url
    )
    assert (
        resolve_service_url("/api/v1/admin/kitchens/abc/branded-page")
        == settings.identity_service_url
    )
    assert (
        resolve_service_url("/api/v1/kitchens/abc/branded-page")
        == settings.identity_service_url
    )
    assert resolve_service_url("/api/v1/admin/customers") == settings.identity_service_url
    assert resolve_service_url("/api/v1/admin/feature-flags") == settings.identity_service_url
    assert resolve_service_url("/api/v1/admin/journeys") == settings.identity_service_url


def test_resolve_service_url_marketing():
    from ckac_common.config import get_settings

    settings = get_settings()
    assert resolve_service_url("/api/v1/marketing/coupons/validate") == settings.marketing_service_url
    assert resolve_service_url("/api/v1/kitchens/abc/crm/customers") == settings.marketing_service_url
    assert resolve_service_url("/api/v1/kitchens/abc/coupons") == settings.marketing_service_url
    assert resolve_service_url("/api/v1/kitchens/abc/promotions/active") == settings.marketing_service_url
    assert (
        resolve_service_url("/api/v1/admin/kitchens/abc/tiffin-summary")
        == settings.marketing_service_url
    )
    assert (
        resolve_service_url("/api/v1/admin/kitchens/abc/subscriptions")
        == settings.marketing_service_url
    )
    assert (
        resolve_service_url("/api/v1/admin/kitchens/abc/subscriptions/xyz/accept")
        == settings.marketing_service_url
    )


def test_resolve_service_url_streaming_admin():
    from ckac_common.config import get_settings

    settings = get_settings()
    assert (
        resolve_service_url("/api/v1/admin/kitchens/abc/stream/summary")
        == settings.streaming_service_url
    )
    assert (
        resolve_service_url("/api/v1/kitchens/abc/stream/settings")
        == settings.streaming_service_url
    )


def test_resolve_service_url_ratings():
    from ckac_common.config import get_settings

    settings = get_settings()
    assert (
        resolve_service_url("/api/v1/customers/me/orders/abc/ratings")
        == settings.ratings_service_url
    )
    assert (
        resolve_service_url("/api/v1/kitchens/abc/dishes/xyz/ratings/summary")
        == settings.ratings_service_url
    )
    assert resolve_service_url("/api/v1/kitchens/abc/suggestions") == settings.ratings_service_url


def test_resolve_service_url_growth():
    from ckac_common.config import get_settings

    settings = get_settings()
    assert resolve_service_url("/api/v1/growth/seasonal-patterns") == settings.growth_service_url
    assert (
        resolve_service_url("/api/v1/kitchens/abc/growth/suggestions")
        == settings.growth_service_url
    )
    assert (
        resolve_service_url("/api/v1/kitchens/abc/growth/daily-menu/push")
        == settings.growth_service_url
    )


def test_resolve_service_url_delivery():
    from ckac_common.config import get_settings

    settings = get_settings()
    assert resolve_service_url("/api/v1/delivery/quote") == settings.delivery_service_url
    assert resolve_service_url("/api/v1/delivery/track/abc123") == settings.delivery_service_url


def test_resolve_service_url_notification():
    from ckac_common.config import get_settings

    settings = get_settings()
    assert resolve_service_url("/api/v1/webhooks/whatsapp") == settings.notification_service_url
    assert resolve_service_url("/api/v1/support/chat") == settings.notification_service_url
    assert resolve_service_url("/api/v1/support/tickets") == settings.notification_service_url
    assert resolve_service_url("/api/v1/admin/tickets") == settings.notification_service_url
    assert resolve_service_url("/api/v1/admin/tickets/abc/reply") == settings.notification_service_url
    assert resolve_service_url("/api/v1/admin/stats") == settings.identity_service_url


@pytest.mark.asyncio
async def test_health_live(gateway_client):
    client, _ = gateway_client
    response = await client.get("/health/live")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_ready_all_ok(gateway_client):
    client, clients = gateway_client
    for name in clients:
        clients[name].get = AsyncMock(return_value=Response(200, json={"status": "ok"}))
    response = await client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "gateway"
    clients["identity"].get.assert_called()
    assert clients["identity"].get.call_args[0][0] == "/health/live"


@pytest.mark.asyncio
async def test_proxy_routes_to_identity(gateway_client):
    client, clients = gateway_client
    clients["identity"].request = AsyncMock(
        return_value=Response(201, content=b'{"ok":true}', headers={"content-type": "application/json"})
    )
    response = await client.post("/api/v1/owners/register", json={"phone": "9876543210", "name": "T"})
    assert response.status_code == 201
    clients["identity"].request.assert_called_once()


@pytest.mark.asyncio
async def test_proxy_routes_to_catalog(gateway_client):
    client, clients = gateway_client
    clients["catalog"].request = AsyncMock(
        return_value=Response(200, content=b'{"dishes":[]}', headers={"content-type": "application/json"})
    )
    response = await client.get("/api/v1/kitchens/abc-uuid/menu")
    assert response.status_code == 200
    clients["catalog"].request.assert_called_once()
    assert "/menu" in clients["catalog"].request.call_args[0][1]


@pytest.mark.asyncio
async def test_proxy_unknown_route_returns_404(gateway_client):
    client, _ = gateway_client
    response = await client.get("/api/v1/unknown")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_proxy_forwards_correlation_id(gateway_client):
    client, clients = gateway_client
    clients["identity"].request = AsyncMock(
        return_value=Response(200, content=b'{}', headers={"content-type": "application/json"})
    )
    response = await client.get(
        "/api/v1/kitchens/me",
        headers={"Authorization": "Bearer test", "X-Correlation-ID": "corr-test-123"},
    )
    assert response.status_code == 200
    assert response.headers.get("X-Correlation-ID") == "corr-test-123"
    forwarded = clients["identity"].request.call_args.kwargs["headers"]
    assert forwarded.get("X-Correlation-ID") == "corr-test-123"


@pytest.mark.asyncio
async def test_proxy_strips_upstream_cors_headers(gateway_client):
    client, clients = gateway_client
    clients["identity"].request = AsyncMock(
        return_value=Response(
            200,
            content=b'{"ok":true}',
            headers={
                "content-type": "application/json",
                "access-control-allow-origin": "https://evil.example",
                "access-control-allow-credentials": "true",
                "date": "Mon, 01 Jan 2020 00:00:00 GMT",
                "server": "identity",
            },
        )
    )
    response = await client.get("/api/v1/kitchens/me")
    assert response.status_code == 200
    lowered = {k.lower() for k in response.headers}
    assert "access-control-allow-origin" not in lowered
    assert response.headers.get("server") != "identity"


@pytest.mark.asyncio
async def test_proxy_generates_correlation_id_when_missing(gateway_client):
    client, _ = gateway_client
    response = await client.get("/health/live")
    assert response.status_code == 200
    cid = response.headers.get("X-Correlation-ID")
    assert cid and len(cid) >= 32


@pytest.mark.asyncio
async def test_openapi_json_aggregates_upstream_specs(gateway_client):
    client, clients = gateway_client
    sample = {
        "openapi": "3.1.0",
        "info": {"title": "identity", "version": "0.1"},
        "paths": {
            "/api/v1/owners/register": {
                "post": {
                    "tags": ["owners"],
                    "summary": "Register",
                    "responses": {"201": {"description": "created"}},
                }
            }
        },
        "components": {"schemas": {}},
    }
    empty = {
        "openapi": "3.1.0",
        "info": {"title": "empty", "version": "0.1"},
        "paths": {},
        "components": {"schemas": {}},
    }

    async def identity_get(url, **_kwargs):
        if url == "/openapi.json":
            return Response(200, json=sample)
        return Response(404, json={"detail": "missing"})

    async def empty_get(url, **_kwargs):
        if url == "/openapi.json":
            return Response(200, json=empty)
        return Response(404, json={"detail": "missing"})

    for name, mock in clients.items():
        if name == "identity":
            mock.get = AsyncMock(side_effect=identity_get)
        else:
            mock.get = AsyncMock(side_effect=empty_get)

    gateway_main._openapi_cache = None
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert data["info"]["title"] == "kitchCU Public API"
    assert "/api/v1/owners/register" in data["paths"]
    assert data["paths"]["/api/v1/owners/register"]["post"]["tags"] == [
        "Identity: owners"
    ]
    assert data["servers"] == SAME_ORIGIN_SERVERS
    assert data["servers"][0]["url"] == ""
    token_url = data["components"]["securitySchemes"]["OAuth2Password"]["flows"]["password"][
        "tokenUrl"
    ]
    assert token_url == "/api/v1/auth/token"


@pytest.mark.asyncio
async def test_openapi_servers_ignore_proxied_http_host(gateway_client):
    """Swagger UI resolves OAuth tokenUrl against servers[0]. An http:// host
    (Caddy/nginx → gateway) becomes mixed-content Failed to fetch on HTTPS /docs.
    """
    client, clients = gateway_client
    empty = {
        "openapi": "3.1.0",
        "info": {"title": "empty", "version": "0.1"},
        "paths": {},
        "components": {"schemas": {}},
    }

    async def empty_get(url, **_kwargs):
        if url == "/openapi.json":
            return Response(200, json=empty)
        return Response(404, json={"detail": "missing"})

    for mock in clients.values():
        mock.get = AsyncMock(side_effect=empty_get)

    gateway_main._openapi_cache = {
        "openapi": "3.1.0",
        "info": {"title": "kitchCU Public API", "version": "1.0.0"},
        "servers": [{"url": "http://kitchcu.com", "description": "API Gateway"}],
        "paths": {},
        "components": {"securitySchemes": {}},
    }
    response = await client.get(
        "/openapi.json",
        headers={"Host": "kitchcu.com", "X-Forwarded-Proto": "http"},
    )
    assert response.status_code == 200
    assert response.json()["servers"] == [
        {"url": "https://kitchcu.com", "description": "API Gateway (this host)"},
    ]


def test_public_gateway_servers_https_on_kitchcu_hosts():
    def _req(host: str, proto: str = "http") -> Request:
        headers = [(b"host", host.encode()), (b"x-forwarded-proto", proto.encode())]
        return Request(
            {
                "type": "http",
                "asgi": {"version": "3.0"},
                "http_version": "1.1",
                "method": "GET",
                "scheme": "http",
                "path": "/openapi.json",
                "raw_path": b"/openapi.json",
                "query_string": b"",
                "headers": headers,
                "client": ("127.0.0.1", 123),
                "server": ("test", 80),
            }
        )

    assert public_gateway_servers(_req("kitchcu.com", "http")) == [
        {"url": "https://kitchcu.com", "description": "API Gateway (this host)"},
    ]
    assert public_gateway_servers(_req("api.kitchcu.com", "http")) == [
        {"url": "https://api.kitchcu.com", "description": "API Gateway (this host)"},
    ]
    assert public_gateway_servers(_req("localhost:18000", "http")) == [
        {"url": "http://localhost:18000", "description": "API Gateway (this host)"},
    ]
    assert public_gateway_servers(_req("test")) == SAME_ORIGIN_SERVERS
    assert SAME_ORIGIN_SERVERS[0]["url"] == ""


@pytest.mark.asyncio
async def test_docs_page_serves_swagger_ui(gateway_client):
    client, _ = gateway_client
    response = await client.get("/docs")
    assert response.status_code == 200
    assert "swagger" in response.text.lower() or "openapi" in response.text.lower()
    assert "tryItOutEnabled" in response.text
    assert "live-responses-table" in response.text
    assert "requestInterceptor" in response.text
    assert "window.location.origin" in response.text


@pytest.mark.asyncio
async def test_cors_allows_kitchcu_subdomains(gateway_client):
    client, _ = gateway_client
    response = await client.options(
        "/health/live",
        headers={
            "Origin": "https://customer.kitchcu.com",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "accept,authorization",
        },
    )
    assert response.status_code in (200, 204)
    assert response.headers.get("access-control-allow-origin") == "https://customer.kitchcu.com"


@pytest.mark.asyncio
async def test_proxy_not_ready_when_clients_empty():
    gateway_main.http_clients = {}
    gateway_main.redis_client = None
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/owners/register", json={})
    assert response.status_code == 503
