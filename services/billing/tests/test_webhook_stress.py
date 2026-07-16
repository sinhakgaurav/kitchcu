"""High-concurrency Razorpay webhook ingress — scaled CI profile (500 parallel)."""

import asyncio

import pytest
from httpx import AsyncClient

# Production target: 20k webhooks/day spikes; CI size/concurrency configurable via env.
from ckac_common.risk_config import webhook_stress_burst_size, webhook_stress_max_concurrency

WEBHOOK_BURST_SIZE = webhook_stress_burst_size()
WEBHOOK_MAX_CONCURRENCY = webhook_stress_max_concurrency()


@pytest.mark.asyncio
async def test_razorpay_webhook_burst_handles_concurrency(client: AsyncClient):
    payload = {"event": "payment.authorized", "payload": {}}
    sem = asyncio.Semaphore(WEBHOOK_MAX_CONCURRENCY)

    async def post_once() -> int:
        async with sem:
            response = await client.post("/api/v1/webhooks/razorpay", json=payload)
            return response.status_code

    results = await asyncio.gather(*[post_once() for _ in range(WEBHOOK_BURST_SIZE)])
    assert all(code == 200 for code in results)
    assert len(results) == WEBHOOK_BURST_SIZE
