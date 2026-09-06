"""Redis-backed rate limiting at the gateway edge (S6 security hardening).

Protects abuse-prone entry points (OTP request/verify, owner registration,
checkout) from brute-force and spam without requiring changes in every domain
service — the gateway is the only public edge (see AGENTS.md "Bypass gateway
for public clients" — forbidden), so this is the single choke point.

Design:
- Fixed-window counter per (client IP, rule) in Redis — `INCR` + `EXPIRE` on
  first hit in the window. O(1), stateless, works across multiple gateway
  replicas (no in-process state) — required for the >=100k concurrent
  session scale target.
- **Fails open** on any Redis error — availability of the platform matters
  more than strict enforcement of a security control during a Redis blip.
- Thresholds are **admin-configurable** (Super Admin → Control). Identity
  persists overrides and publishes JSON to Redis key ``ckac:gateway:rate_limits``;
  this module caches that payload in-process for ``CACHE_TTL_SECONDS``.
- Most routes get a generous default budget; only the specific abuse-prone
  routes below get tight budgets.
"""

from __future__ import annotations

import ipaddress
import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from fastapi import Request

from ckac_common.rate_limits import (
    CACHE_TTL_SECONDS,
    DEFAULT_RULES,
    REDIS_KEY,
    merge_rules,
    normalize_payload,
)


@dataclass(frozen=True)
class RateLimitRule:
    name: str
    limit: int
    window_seconds: int
    match: Callable[[str, str], bool]


def _otp_request(method: str, path: str) -> bool:
    if method != "POST":
        return False
    return path in (
        "/api/v1/auth/otp/request",
        "/api/v1/auth/customer/whatsapp/request",
    )


def _otp_verify(method: str, path: str) -> bool:
    if method != "POST":
        return False
    return path in (
        "/api/v1/auth/otp/verify",
        "/api/v1/auth/customer/whatsapp/verify",
    )


def _owner_register(method: str, path: str) -> bool:
    return method == "POST" and path == "/api/v1/owners/register"


def _checkout(method: str, path: str) -> bool:
    return method == "POST" and (
        path.endswith("/orders/customer") or path.endswith("/orders/customer/master")
    )


def _default(_method: str, _path: str) -> bool:
    return True


_MATCHERS: dict[str, Callable[[str, str], bool]] = {
    "otp_request": _otp_request,
    "otp_verify": _otp_verify,
    "owner_register": _owner_register,
    "checkout": _checkout,
    "default": _default,
}

# Order matters — first match wins, "default" is always the fallback.
_RULE_ORDER = ("otp_request", "otp_verify", "owner_register", "checkout", "default")

# Built from defaults; rebuilt when admin overrides refresh.
RULES: tuple[RateLimitRule, ...] = tuple(
    RateLimitRule(
        name=name,
        limit=DEFAULT_RULES[name]["limit"],
        window_seconds=DEFAULT_RULES[name]["window_seconds"],
        match=_MATCHERS[name],
    )
    for name in _RULE_ORDER
)

# Docker bridge networks the on-host seed scripts appear to come from.
_OPS_NETWORKS = tuple(
    ipaddress.ip_network(cidr)
    for cidr in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "fd00::/8")
)

_config_cache: dict[str, Any] = {
    "loaded_at": 0.0,
    "enabled": True,
    "rules": {k: dict(v) for k, v in DEFAULT_RULES.items()},
}


def _build_rules(rule_cfg: dict[str, dict[str, int]]) -> tuple[RateLimitRule, ...]:
    return tuple(
        RateLimitRule(
            name=name,
            limit=int(rule_cfg[name]["limit"]),
            window_seconds=int(rule_cfg[name]["window_seconds"]),
            match=_MATCHERS[name],
        )
        for name in _RULE_ORDER
    )


def apply_config(payload: dict[str, Any] | None) -> None:
    """Apply a normalized config payload (tests + Redis refresh)."""
    global RULES
    normalized = normalize_payload(payload)
    _config_cache["enabled"] = bool(normalized["enabled"])
    _config_cache["rules"] = merge_rules(normalized["rules"])
    _config_cache["loaded_at"] = time.monotonic()
    RULES = _build_rules(_config_cache["rules"])


def reset_config_for_tests() -> None:
    """Restore code defaults (unit tests)."""
    apply_config({"enabled": True, "rules": {k: dict(v) for k, v in DEFAULT_RULES.items()}})


async def _refresh_config_from_redis(redis_client) -> None:
    now = time.monotonic()
    if now - float(_config_cache["loaded_at"]) < CACHE_TTL_SECONDS:
        return
    if redis_client is None:
        _config_cache["loaded_at"] = now
        return
    try:
        raw = await redis_client.get(REDIS_KEY)
        if not raw:
            _config_cache["loaded_at"] = now
            return
        data = json.loads(raw) if isinstance(raw, str) else raw
        if isinstance(data, dict):
            apply_config(data)
        else:
            _config_cache["loaded_at"] = now
    except Exception:
        _config_cache["loaded_at"] = now


def resolve_rule(method: str, path: str) -> RateLimitRule:
    for rule in RULES[:-1]:
        if rule.match(method, path):
            return rule
    return RULES[-1]


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def is_local_ops_client(request: Request) -> bool:
    """True for on-host ops traffic (VM seed scripts), false for anything proxied.

    Two conditions, both required:

    1. The TCP peer is loopback or a private address. Seed scripts curl
       ``127.0.0.1:18000``, but Docker's userland proxy rewrites the peer to the
       bridge gateway (``172.17.0.1`` and friends), so a loopback-only check never
       fires in the compose deployment — which left the VM seed scripts throttling
       themselves for hours on the OTP rule.
    2. There is no ``X-Forwarded-For`` header. Caddy is the only path a public
       client has to the gateway (the port is bound to 127.0.0.1 on the VM) and it
       always sets that header, so its presence marks the request as untrusted.

    The peer is read from ``request.client.host`` only, never from a header, so a
    public client cannot spoof its way into the exemption.
    """
    host = (request.client.host if request.client else "") or ""
    if request.headers.get("x-forwarded-for"):
        return False
    if host in ("127.0.0.1", "::1", "localhost"):
        return True
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        return False
    # Explicit RFC1918 / loopback only. `ipaddress.is_private` is too broad here —
    # it also covers documentation ranges like 203.0.113.0/24, which are routable
    # from the internet's point of view and must stay rate limited.
    return addr.is_loopback or any(addr in net for net in _OPS_NETWORKS)


async def check_rate_limit(redis_client, request: Request, path: str) -> tuple[bool, int, str]:
    """Returns ``(allowed, retry_after_seconds, rule_name)``.

    Fails open (``allowed=True``) when Redis is unavailable or returns an
    unexpected type — enforcement is best-effort, not a hard dependency.
    On-host ops traffic is not limited so the GCP seed scripts can finish; see
    :func:`is_local_ops_client`. When admin disables limiting, all requests are
    allowed.
    """
    await _refresh_config_from_redis(redis_client)
    rule = resolve_rule(request.method, path)
    if not _config_cache.get("enabled", True):
        return True, 0, rule.name
    if is_local_ops_client(request):
        return True, 0, rule.name
    if redis_client is None:
        return True, 0, rule.name

    key = f"ratelimit:{rule.name}:{client_ip(request)}"
    try:
        count = int(await redis_client.incr(key))
        if count == 1:
            await redis_client.expire(key, rule.window_seconds)
        if count > rule.limit:
            ttl = await redis_client.ttl(key)
            retry_after = int(ttl) if isinstance(ttl, int) and ttl > 0 else rule.window_seconds
            return False, retry_after, rule.name
        return True, 0, rule.name
    except Exception:
        return True, 0, rule.name
