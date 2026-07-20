"""F19b — pantry deduct triggers on order ready, not accept."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_stock_deduct_called_on_ready_not_accept(client: AsyncClient, order_ctx, manual_order_payload):
    _, kitchen_id, _, _, token = order_ctx
    headers = {"Authorization": f"Bearer {token}"}
    create = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/orders/manual",
        json=manual_order_payload,
        headers=headers,
    )
    assert create.status_code == 201, create.text
    order_id = create.json()["id"]

    mock_deduct = AsyncMock(return_value={"deducted": [], "low_stock_alerts": []})
    with patch("app.routes.deduct_order_stock", mock_deduct):
        accept = await client.patch(
            f"/api/v1/orders/{order_id}/status",
            json={"status": "accepted"},
            headers=headers,
        )
        assert accept.status_code == 200
        assert mock_deduct.await_count == 0

        preparing = await client.patch(
            f"/api/v1/orders/{order_id}/status",
            json={"status": "preparing"},
            headers=headers,
        )
        assert preparing.status_code == 200
        assert mock_deduct.await_count == 0

        ready = await client.patch(
            f"/api/v1/orders/{order_id}/status",
            json={"status": "ready"},
            headers=headers,
        )
        assert ready.status_code == 200
        assert mock_deduct.await_count == 1
        args = mock_deduct.await_args.args
        assert str(args[0]) == str(kitchen_id)
        assert str(args[1]) == str(order_id)
        assert isinstance(args[2], list) and len(args[2]) >= 1
