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

import json
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient, Response

from app import main as gateway_main
from app.main import app, resolve_service_url


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
    assert resolve_service_url("/api/v1/kitchens/me") == settings.identity_service_url


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


def test_resolve_service_url_customer_orders():
    from ckac_common.config import get_settings

    settings = get_settings()
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


def test_resolve_service_url_marketing():
    from ckac_common.config import get_settings

    settings = get_settings()
    assert resolve_service_url("/api/v1/marketing/coupons/validate") == settings.marketing_service_url
    assert resolve_service_url("/api/v1/kitchens/abc/crm/customers") == settings.marketing_service_url
    assert resolve_service_url("/api/v1/kitchens/abc/coupons") == settings.marketing_service_url
    assert resolve_service_url("/api/v1/kitchens/abc/promotions/active") == settings.marketing_service_url


def test_resolve_service_url_ratings():
    from ckac_common.config import get_settings

    settings = get_settings()
    assert (
        resolve_service_url("/api/v1/customers/me/orders/abc/ratings")
        == settings.ratings_service_url
    )
    assert (
        resolve_service_url(f"/api/v1/kitchens/abc/dishes/xyz/ratings/summary")
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
    clients["identity"].get = AsyncMock(return_value=Response(200, json={"status": "ok"}))
    clients["catalog"].get = AsyncMock(return_value=Response(200, json={"status": "ok"}))
    clients["order"].get = AsyncMock(return_value=Response(200, json={"status": "ok"}))
    clients["billing"].get = AsyncMock(return_value=Response(200, json={"status": "ok"}))
    clients["notification"].get = AsyncMock(return_value=Response(200, json={"status": "ok"}))
    clients["marketing"].get = AsyncMock(return_value=Response(200, json={"status": "ok"}))
    clients["ratings"].get = AsyncMock(return_value=Response(200, json={"status": "ok"}))
    clients["growth"].get = AsyncMock(return_value=Response(200, json={"status": "ok"}))
    clients["delivery"].get = AsyncMock(return_value=Response(200, json={"status": "ok"}))
    response = await client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "gateway"


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
async def test_proxy_generates_correlation_id_when_missing(gateway_client):
    client, _ = gateway_client
    response = await client.get("/health/live")
    assert response.status_code == 200
    cid = response.headers.get("X-Correlation-ID")
    assert cid and len(cid) >= 32


@pytest.mark.asyncio
async def test_proxy_not_ready_when_clients_empty():
    gateway_main.http_clients = {}
    gateway_main.redis_client = None
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/owners/register", json={})
    assert response.status_code == 503
