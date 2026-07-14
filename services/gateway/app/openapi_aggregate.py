"""Aggregate per-service OpenAPI specs into one gateway contract."""

from __future__ import annotations

from typing import Any

import httpx

GATEWAY_INFO = {
    "title": "kitchCU Public API",
    "version": "1.0.0",
    "description": (
        "Unified OpenAPI contract exposed through the API Gateway. "
        "All public clients call /api/v1/* on the gateway; paths below are "
        "merged from identity, catalog, order, billing, marketing, ratings, "
        "growth, delivery, learning, community, streaming, and notification."
    ),
}

SERVICE_LABELS = {
    "identity": "Identity",
    "catalog": "Catalog",
    "order": "Order",
    "billing": "Billing",
    "notification": "Notification",
    "marketing": "Marketing",
    "ratings": "Ratings",
    "growth": "Growth",
    "delivery": "Delivery",
    "learning": "Learning",
    "community": "Community",
    "streaming": "Streaming",
}


def _prefix_ref(ref: str, prefix: str) -> str:
    marker = "#/components/schemas/"
    if not ref.startswith(marker):
        return ref
    name = ref[len(marker) :]
    return f"{marker}{prefix}{name}"


def _rewrite_refs(node: Any, prefix: str) -> Any:
    if isinstance(node, dict):
        out: dict[str, Any] = {}
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str):
                out[key] = _prefix_ref(value, prefix)
            else:
                out[key] = _rewrite_refs(value, prefix)
        return out
    if isinstance(node, list):
        return [_rewrite_refs(item, prefix) for item in node]
    return node


def merge_openapi_specs(
    specs: list[tuple[str, dict[str, Any]]],
    *,
    servers: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Merge service OpenAPI documents into a single gateway schema."""
    merged: dict[str, Any] = {
        "openapi": "3.1.0",
        "info": dict(GATEWAY_INFO),
        "servers": servers
        or [
            {"url": "/", "description": "API Gateway (same origin / proxied)"},
        ],
        "tags": [],
        "paths": {},
        "components": {
            "schemas": {},
            "securitySchemes": {
                "HTTPBearer": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                    "description": "Owner, customer, or admin JWT from Identity",
                }
            },
        },
    }
    tag_names: set[str] = set()
    openapi_versions: list[str] = []

    for service_key, spec in specs:
        if not isinstance(spec, dict):
            continue
        label = SERVICE_LABELS.get(service_key, service_key.title())
        prefix = f"{service_key}_"
        version = spec.get("openapi")
        if isinstance(version, str):
            openapi_versions.append(version)

        schemas = (spec.get("components") or {}).get("schemas") or {}
        for name, schema in schemas.items():
            merged["components"]["schemas"][f"{prefix}{name}"] = _rewrite_refs(
                schema, prefix
            )

        for scheme_name, scheme in (
            (spec.get("components") or {}).get("securitySchemes") or {}
        ).items():
            if scheme_name not in merged["components"]["securitySchemes"]:
                merged["components"]["securitySchemes"][scheme_name] = scheme

        for path, methods in (spec.get("paths") or {}).items():
            if path in ("/health/live", "/health/ready", "/openapi.json", "/docs", "/redoc"):
                continue
            rewritten = _rewrite_refs(methods, prefix)
            if isinstance(rewritten, dict):
                for method, operation in rewritten.items():
                    if not isinstance(operation, dict):
                        continue
                    tags = operation.get("tags") or []
                    if not tags:
                        tags = [label]
                    else:
                        tags = [f"{label}: {t}" for t in tags]
                    operation["tags"] = tags
                    for tag in tags:
                        if tag not in tag_names:
                            tag_names.add(tag)
                            merged["tags"].append(
                                {"name": tag, "description": f"Owned by {label} service"}
                            )
                    operation.setdefault(
                        "x-kitchcu-service",
                        service_key,
                    )
            merged["paths"][path] = rewritten

    if openapi_versions and all(v.startswith("3.0") for v in openapi_versions):
        merged["openapi"] = "3.0.3"

    return merged


async def fetch_service_openapi(
    clients: dict[str, httpx.AsyncClient],
) -> list[tuple[str, dict[str, Any]]]:
    collected: list[tuple[str, dict[str, Any]]] = []
    for key, client in clients.items():
        try:
            response = await client.get("/openapi.json")
            if response.status_code != 200:
                continue
            data = response.json()
            if isinstance(data, dict) and "paths" in data:
                collected.append((key, data))
        except Exception:
            continue
    return collected


async def build_gateway_openapi(
    clients: dict[str, httpx.AsyncClient],
    *,
    servers: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    specs = await fetch_service_openapi(clients)
    return merge_openapi_specs(specs, servers=servers)
