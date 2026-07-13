"""Standard health check responses — all services use the same shape."""


def live_response(service: str) -> dict[str, str]:
    return {"status": "ok", "service": service}


async def ready_response(
    service: str,
    *,
    database: bool,
    redis: bool | None = None,
) -> dict:
    checks: dict = {"database": database}
    if redis is not None:
        checks["redis"] = redis
    all_ok = all(checks.values())
    return {"status": "ok" if all_ok else "degraded", "service": service, **checks}


async def gateway_ready_response(
    service: str,
    *,
    redis: bool,
    services: dict[str, bool],
) -> dict:
    all_ok = redis and all(services.values()) if services else False
    return {
        "status": "ok" if all_ok else "degraded",
        "service": service,
        "redis": redis,
        "services": services,
    }
