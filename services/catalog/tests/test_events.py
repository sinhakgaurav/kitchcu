import io
import json

import pytest
from httpx import AsyncClient
from openpyxl import Workbook

from app.dish_bulk import BULK_HEADERS
from tests.conftest import build_dish_payload


def _minimal_jpeg() -> bytes:
    return bytes.fromhex(
        "ffd8ffe000104a46494600010100000100010000ffdb004300080606070605080707"
        "070909080a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c20242e2720222c231c"
        "1c2837292c30313434341f27393d38323c2e333432ffdb0043010909090c0b0c180d"
        "0d1832211c2132323232323232323232323232323232323232323232323232323232"
        "323232323232323232323232323232323232323232ffc00011080001000103011100"
        "021101031101ffc40014000100000000000000000000000000000000ffc400141001"
        "00000000000000000000000000000000ffda000c0301000210031000003f00bf80ffd9"
    )


def _bulk_xlsx() -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "dishes"
    ws.append(BULK_HEADERS)
    ws.append(
        [
            "Event Bulk Dish",
            "north_indian",
            "veg",
            150,
            25,
            15,
            40,
            "Desc",
            "Ing",
            "Quality",
            "FALSE",
            "FALSE",
            "FALSE",
            "event_bulk.jpg",
        ]
    )
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_dish_created_publishes_redis_event(client: AsyncClient, kitchen_ctx):
    from app.main import redis_client

    if redis_client:
        await redis_client.delete("ckac:catalog:dish")

    _, kitchen_id, token = kitchen_ctx
    payload = await build_dish_payload(client, kitchen_id, token)
    response = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/dishes",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    dish_id = response.json()["id"]

    from app.main import redis_client

    assert redis_client is not None
    messages = await redis_client.xread({"ckac:catalog:dish": "0-0"}, count=10)
    assert len(messages) >= 1
    stream_name, entries = messages[0]
    assert stream_name == "ckac:catalog:dish"
    event_data = json.loads(entries[-1][1]["data"])
    assert event_data["event_type"] == "dish.created"
    assert event_data["aggregate_id"] == dish_id
    assert event_data["producer"] == "catalog-service"
    assert event_data["payload"]["kitchen_id"] == str(kitchen_id)


@pytest.mark.asyncio
async def test_dish_updated_publishes_event(client: AsyncClient, kitchen_ctx):
    _, kitchen_id, token = kitchen_ctx
    headers = {"Authorization": f"Bearer {token}"}
    payload = await build_dish_payload(client, kitchen_id, token)
    create = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/dishes",
        json=payload,
        headers=headers,
    )
    dish_id = create.json()["id"]

    response = await client.patch(
        f"/api/v1/kitchens/{kitchen_id}/dishes/{dish_id}",
        json={"price": 249.0},
        headers=headers,
    )
    assert response.status_code == 200

    from app.main import redis_client

    messages = await redis_client.xread({"ckac:catalog:dish": "0-0"}, count=20)
    events = [json.loads(entry[1]["data"]) for _, entries in messages for entry in entries]
    updated = [e for e in events if e["event_type"] == "dish.updated"]
    assert len(updated) >= 1
    assert updated[-1]["aggregate_id"] == dish_id
    assert "price" in updated[-1]["payload"]["changes"]


@pytest.mark.asyncio
async def test_bulk_import_publishes_dish_created_per_row(client: AsyncClient, kitchen_ctx):
    """EDD: each accepted bulk row must publish dish.created on ckac:catalog:dish."""
    from app.main import redis_client

    if redis_client:
        await redis_client.delete("ckac:catalog:dish")

    _, kitchen_id, token = kitchen_ctx
    res = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/dishes/bulk",
        headers={"Authorization": f"Bearer {token}"},
        files={
            "spreadsheet": (
                "dishes.xlsx",
                _bulk_xlsx(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
            "images": ("event_bulk.jpg", _minimal_jpeg(), "image/jpeg"),
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["accepted"] == 1
    dish_id = body["results"][0]["dish_id"]

    assert redis_client is not None
    messages = await redis_client.xread({"ckac:catalog:dish": "0-0"}, count=20)
    events = [json.loads(entry[1]["data"]) for _, entries in messages for entry in entries]
    created = [
        e
        for e in events
        if e["event_type"] == "dish.created" and e["aggregate_id"] == dish_id
    ]
    assert len(created) == 1
    assert created[0]["producer"] == "catalog-service"
    assert created[0]["payload"]["kitchen_id"] == str(kitchen_id)
    assert created[0]["payload"]["name"] == "Event Bulk Dish"
