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
  A gateway that 503s all traffic because Redis hiccuped is a worse outcome
  than a rate limiter that briefly stops limiting.
- Most routes get a generous default budget; only the specific abuse-prone
  routes below get tight budgets.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Request


@dataclass(frozen=True)
class RateLimitRule:
    name: str
    limit: int
    window_seconds: int
    match: Callable[[str, str], bool]


def _otp_request(method: str, path: str) -> bool:
    return method == "POST" and path == "/api/v1/auth/otp/request"


def _otp_verify(method: str, path: str) -> bool:
    return method == "POST" and path == "/api/v1/auth/otp/verify"


def _owner_register(method: str, path: str) -> bool:
    return method == "POST" and path == "/api/v1/owners/register"


def _checkout(method: str, path: str) -> bool:
    return method == "POST" and (
        path.endswith("/orders/customer") or path.endswith("/orders/customer/master")
    )


def _default(_method: str, _path: str) -> bool:
    return True


# Order matters — first match wins, "default" is always the fallback.
RULES: tuple[RateLimitRule, ...] = (
    RateLimitRule("otp_request", limit=5, window_seconds=600, match=_otp_request),
    RateLimitRule("otp_verify", limit=10, window_seconds=600, match=_otp_verify),
    RateLimitRule("owner_register", limit=10, window_seconds=3600, match=_owner_register),
    RateLimitRule("checkout", limit=30, window_seconds=60, match=_checkout),
    RateLimitRule("default", limit=600, window_seconds=60, match=_default),
)


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


async def check_rate_limit(redis_client, request: Request, path: str) -> tuple[bool, int, str]:
    """Returns ``(allowed, retry_after_seconds, rule_name)``.

    Fails open (``allowed=True``) when Redis is unavailable or returns an
    unexpected type — enforcement is best-effort, not a hard dependency.
    """
    rule = resolve_rule(request.method, path)
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
