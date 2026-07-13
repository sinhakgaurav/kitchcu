"""Notification service webhook tests — Sprint 4."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient, Response

from app.whatsapp import extract_messages
from tests.conftest import WEBHOOK_PAYLOAD, _seed_kitchen


def test_extract_whatsapp_messages():
    msgs = extract_messages(WEBHOOK_PAYLOAD)
    assert len(msgs) == 1
    assert msgs[0].text == "2 Paneer Tikka"
    assert msgs[0].phone_number_id == "PHONE123"


@pytest.mark.asyncio
async def test_webhook_verify(client: AsyncClient):
    response = await client.get(
        "/api/v1/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "ckac-dev-verify",
            "hub.challenge": "12345",
        },
    )
    assert response.status_code == 200
    assert response.json() == 12345


@pytest.mark.asyncio
async def test_webhook_creates_draft_via_order_service(client: AsyncClient):
    kitchen_id = _seed_kitchen()
    mock_response = Response(
        201,
        json={
            "id": str(uuid.uuid4()),
            "kitchen_id": str(kitchen_id),
            "status": "draft",
            "source": "whatsapp",
            "raw_message": "2 Paneer Tikka",
            "parsed_items": [],
            "unmatched_lines": [],
            "special_notes": [],
            "order_id": None,
            "created_at": "2026-07-12T00:00:00Z",
        },
    )
    with patch("app.routes.process_inbound_message", new_callable=AsyncMock) as mock_proc:
        mock_proc.return_value = {
            "status": "draft_created",
            "draft_id": "abc",
            "kitchen_id": str(kitchen_id),
        }
        response = await client.post("/api/v1/webhooks/whatsapp", json=WEBHOOK_PAYLOAD)
    assert response.status_code == 200
    assert response.json()["processed"] == 1
