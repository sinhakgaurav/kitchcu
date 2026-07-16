"""Outbox DLQ — failed Redis publish lands in ckac_events.outbox_dlq (TDD)."""

import json
from unittest.mock import AsyncMock, patch

import psycopg2
import pytest
from httpx import AsyncClient

from tests.conftest import SYNC_DB_URL


@pytest.mark.asyncio
async def test_failed_redis_publish_writes_outbox_dlq(client: AsyncClient, billing_ctx):
    _, _, order_id, _, token = billing_ctx
    headers = {"Authorization": f"Bearer {token}"}

    from app.main import redis_client

    assert redis_client is not None

    with patch.object(redis_client, "xadd", new_callable=AsyncMock) as mock_xadd:
        mock_xadd.side_effect = RuntimeError("redis spike simulated")

        create = await client.post(
            "/api/v1/billing/payments",
            json={"order_id": str(order_id), "method": "online"},
            headers=headers,
        )
        assert create.status_code == 201

    conn = psycopg2.connect(SYNC_DB_URL)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT o.event_type, d.stream_key, o.published
            FROM ckac_events.outbox o
            JOIN ckac_events.outbox_dlq d ON d.event_id = o.event_id
            WHERE o.event_type = 'payment.created'
            LIMIT 1
            """
        )
        row = cur.fetchone()
        assert row is not None
        event_type, stream_key, published = row
        assert event_type == "payment.created"
        assert stream_key == "ckac:billing:payment"
        assert published is False

        cur.execute("SELECT error_message, payload FROM ckac_events.outbox_dlq LIMIT 1")
        dlq_row = cur.fetchone()
        assert dlq_row is not None
        assert "redis spike" in dlq_row[0]
        payload = dlq_row[1]
        if isinstance(payload, str):
            payload = json.loads(payload)
        assert "payment_id" in payload or "order_id" in payload
    conn.close()
