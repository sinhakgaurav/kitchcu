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
from fastapi import Request
from httpx import ASGITransport, AsyncClient

from app import main as gateway_main
from app.main import app
from app.rate_limit import (
    apply_config,
    check_rate_limit,
    client_ip,
    is_local_ops_client,
    reset_config_for_tests,
    resolve_rule,
)


@pytest.fixture(autouse=True)
def _reset_rate_limit_config():
    reset_config_for_tests()
    yield
    reset_config_for_tests()


def _fake_request(method: str = "GET", ip: str = "1.2.3.4", forwarded: str | None = None) -> Request:
    headers = []
    if forwarded:
        headers.append((b"x-forwarded-for", forwarded.encode()))
    scope = {
        "type": "http",
        "method": method,
        "path": "/",
        "headers": headers,
        "client": (ip, 12345),
    }
    return Request(scope)


def test_resolve_rule_matches_otp_request():
    rule = resolve_rule("POST", "/api/v1/auth/otp/request")
    assert rule.name == "otp_request"
    assert rule.limit == 5


def test_resolve_rule_matches_customer_whatsapp_otp():
    assert resolve_rule("POST", "/api/v1/auth/customer/whatsapp/request").name == "otp_request"
    assert resolve_rule("POST", "/api/v1/auth/customer/whatsapp/verify").name == "otp_verify"


def test_resolve_rule_matches_otp_verify():
    rule = resolve_rule("POST", "/api/v1/auth/otp/verify")
    assert rule.name == "otp_verify"


def test_apply_config_overrides_limits():
    apply_config(
        {
            "enabled": True,
            "rules": {"otp_request": {"limit": 99, "window_seconds": 120}},
        }
    )
    rule = resolve_rule("POST", "/api/v1/auth/otp/request")
    assert rule.limit == 99
    assert rule.window_seconds == 120


@pytest.mark.asyncio
async def test_check_rate_limit_skips_when_disabled():
    apply_config({"enabled": False, "rules": {}})
    redis = AsyncMock()
    redis.incr = AsyncMock(return_value=999)
    req = _fake_request(method="POST")
    allowed, retry_after, rule_name = await check_rate_limit(redis, req, "/api/v1/auth/otp/request")
    assert allowed is True
    assert retry_after == 0
    assert rule_name == "otp_request"
    redis.incr.assert_not_called()


def test_resolve_rule_matches_owner_register():
    rule = resolve_rule("POST", "/api/v1/owners/register")
    assert rule.name == "owner_register"


def test_resolve_rule_matches_checkout():
    rule = resolve_rule("POST", "/api/v1/kitchens/abc/orders/customer")
    assert rule.name == "checkout"


def test_resolve_rule_falls_back_to_default():
    rule = resolve_rule("GET", "/api/v1/kitchens/abc/menu")
    assert rule.name == "default"
    assert rule.limit == 600


def test_client_ip_prefers_x_forwarded_for():
    req = _fake_request(ip="10.0.0.1", forwarded="203.0.113.9, 10.0.0.1")
    assert client_ip(req) == "203.0.113.9"


def test_client_ip_falls_back_to_direct_client():
    req = _fake_request(ip="10.0.0.1")
    assert client_ip(req) == "10.0.0.1"


def test_is_local_ops_client_accepts_loopback():
    assert is_local_ops_client(_fake_request(ip="127.0.0.1")) is True
    assert is_local_ops_client(_fake_request(ip="::1")) is True
    assert is_local_ops_client(_fake_request(ip="1.2.3.4")) is False


def test_is_local_ops_client_accepts_the_docker_bridge_peer():
    """Seed scripts curl 127.0.0.1:18000, but Docker rewrites the peer to the bridge.

    Without this the loopback exemption never fires in the compose deployment and
    the VM seed scripts throttle themselves for hours on the OTP rule.
    """
    for bridge_ip in ("172.17.0.1", "172.24.0.1", "192.168.65.1", "10.0.0.5"):
        assert is_local_ops_client(_fake_request(ip=bridge_ip)) is True, bridge_ip


def test_is_local_ops_client_rejects_proxied_traffic():
    """Caddy always sets X-Forwarded-For, so public traffic is never exempt.

    This is the whole safety property: the gateway port is bound to 127.0.0.1 on the
    VM, so the only way a public client reaches it is through Caddy — and that path
    always carries the header.
    """
    proxied = _fake_request(ip="172.17.0.1", forwarded="203.0.113.9")
    assert is_local_ops_client(proxied) is False
    # A spoofed XFF claiming loopback must not win either.
    spoofed = _fake_request(ip="203.0.113.9", forwarded="127.0.0.1")
    assert is_local_ops_client(spoofed) is False


def test_is_local_ops_client_rejects_a_public_peer():
    assert is_local_ops_client(_fake_request(ip="203.0.113.9")) is False


@pytest.mark.asyncio
async def test_check_rate_limit_skips_loopback_even_when_over_limit():
    redis = AsyncMock()
    redis.incr = AsyncMock(return_value=999)
    req = _fake_request(method="POST", ip="127.0.0.1")
    allowed, retry_after, rule_name = await check_rate_limit(redis, req, "/api/v1/auth/otp/request")
    assert allowed is True
    assert retry_after == 0
    assert rule_name == "otp_request"
    redis.incr.assert_not_called()


@pytest.mark.asyncio
async def test_check_rate_limit_skips_docker_bridge_seed_traffic():
    redis = AsyncMock()
    redis.incr = AsyncMock(return_value=999)
    req = _fake_request(method="POST", ip="172.17.0.1")
    allowed, retry_after, _rule = await check_rate_limit(redis, req, "/api/v1/auth/otp/request")
    assert allowed is True
    assert retry_after == 0
    redis.incr.assert_not_called()


@pytest.mark.asyncio
async def test_check_rate_limit_still_limits_proxied_traffic_from_the_bridge():
    redis = AsyncMock()
    redis.incr = AsyncMock(return_value=6)
    redis.ttl = AsyncMock(return_value=400)
    req = _fake_request(method="POST", ip="172.17.0.1", forwarded="203.0.113.9")
    allowed, retry_after, rule_name = await check_rate_limit(redis, req, "/api/v1/auth/otp/request")
    assert allowed is False
    assert retry_after == 400
    assert rule_name == "otp_request"


@pytest.mark.asyncio
async def test_check_rate_limit_allows_when_redis_is_none():
    req = _fake_request(method="POST")
    allowed, retry_after, rule_name = await check_rate_limit(None, req, "/api/v1/auth/otp/request")
    assert allowed is True
    assert retry_after == 0
    assert rule_name == "otp_request"


@pytest.mark.asyncio
async def test_check_rate_limit_blocks_after_limit_exceeded():
    redis = AsyncMock()
    redis.incr = AsyncMock(return_value=6)  # over the otp_request limit of 5
    redis.ttl = AsyncMock(return_value=400)
    req = _fake_request(method="POST")
    allowed, retry_after, rule_name = await check_rate_limit(redis, req, "/api/v1/auth/otp/request")
    assert allowed is False
    assert retry_after == 400
    assert rule_name == "otp_request"


@pytest.mark.asyncio
async def test_check_rate_limit_allows_under_limit():
    redis = AsyncMock()
    redis.incr = AsyncMock(return_value=3)
    req = _fake_request(method="POST")
    allowed, _retry_after, _rule = await check_rate_limit(redis, req, "/api/v1/auth/otp/request")
    assert allowed is True


@pytest.mark.asyncio
async def test_check_rate_limit_fails_open_on_redis_error():
    redis = AsyncMock()
    redis.incr = AsyncMock(side_effect=ConnectionError("redis down"))
    req = _fake_request(method="POST")
    allowed, retry_after, _rule = await check_rate_limit(redis, req, "/api/v1/auth/otp/request")
    assert allowed is True
    assert retry_after == 0


@pytest.mark.asyncio
async def test_proxy_returns_429_when_rate_limited():
    mock_redis = AsyncMock()
    mock_redis.incr = AsyncMock(return_value=6)
    mock_redis.ttl = AsyncMock(return_value=300)
    identity = AsyncMock()
    gateway_main.redis_client = mock_redis
    gateway_main.http_clients = {"identity": identity}
    # Non-loopback peer — loopback is exempt (GCP seed via 127.0.0.1).
    transport = ASGITransport(app=app, client=("203.0.113.50", 50000))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/otp/request", json={"phone": "9876543210"}
        )
    assert response.status_code == 429
    assert response.headers.get("Retry-After") == "300"
    identity.request.assert_not_called()
    gateway_main.redis_client = None
    gateway_main.http_clients = {}
