"""Correlation ID context propagation — closes the "can trace HTTP hops but not the
event chain they trigger" observability gap. `CorrelationMiddleware` stamps a
contextvar for the duration of the request; `EventPublisher.build()` reads it so every
event published during that request carries the same correlation ID without every
domain/schema function needing to thread it through as a parameter."""

import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from ckac_common.event_bus import EventPublisher
from ckac_common.observability import (
    CORRELATION_ID_HEADER,
    CorrelationMiddleware,
    get_correlation_id,
)


def test_get_correlation_id_is_none_outside_a_request():
    assert get_correlation_id() is None


def test_event_publisher_build_defaults_to_none_outside_a_request():
    event = EventPublisher.build(
        event_type="test.event",
        aggregate_type="test",
        aggregate_id="1",
        producer="test-service",
        payload={},
    )
    assert event.correlation_id is None


def test_event_publisher_build_respects_explicit_correlation_id():
    event = EventPublisher.build(
        event_type="test.event",
        aggregate_type="test",
        aggregate_id="1",
        producer="test-service",
        payload={},
        correlation_id="explicit-id-123",
    )
    assert event.correlation_id == "explicit-id-123"


def test_correlation_middleware_stamps_events_built_during_the_request():
    captured: dict = {}

    async def handler(request):
        event = EventPublisher.build(
            event_type="test.event",
            aggregate_type="test",
            aggregate_id="1",
            producer="test-service",
            payload={},
        )
        captured["correlation_id"] = event.correlation_id
        return JSONResponse({"ok": True})

    app = Starlette(routes=[Route("/", handler)])
    app.add_middleware(CorrelationMiddleware)
    client = TestClient(app)

    response = client.get("/", headers={CORRELATION_ID_HEADER: "req-corr-abc"})
    assert response.status_code == 200
    assert captured["correlation_id"] == "req-corr-abc"
    assert response.headers[CORRELATION_ID_HEADER] == "req-corr-abc"


def test_correlation_context_does_not_leak_between_requests():
    captured: list[str | None] = []

    async def handler(request):
        captured.append(get_correlation_id())
        return JSONResponse({"ok": True})

    app = Starlette(routes=[Route("/", handler)])
    app.add_middleware(CorrelationMiddleware)
    client = TestClient(app)

    client.get("/", headers={CORRELATION_ID_HEADER: "first-request"})
    client.get("/", headers={CORRELATION_ID_HEADER: "second-request"})

    assert captured == ["first-request", "second-request"]
    assert get_correlation_id() is None
