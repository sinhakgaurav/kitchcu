"""Customer discovery home feed — near you, featured, liked, cheapest dishes."""

import pytest
from httpx import AsyncClient

from tests.test_kitchens import KITCHEN_PAYLOAD


@pytest.mark.asyncio
async def test_discovery_home_empty_area(client: AsyncClient):
    resp = await client.get(
        "/api/v1/discovery/home",
        params={"latitude": 28.6139, "longitude": 77.2090, "max_km": 10},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["near_you"] == []
    assert data["featured"] == []
    assert data["most_liked"] == []
    assert data["live_now"] == []
    assert data["cheapest_dishes"] == []
    assert data["customer_latitude"] == 28.6139


@pytest.mark.asyncio
async def test_discovery_home_includes_nearby_kitchen(client: AsyncClient, auth_headers: dict):
    created = await client.post("/api/v1/kitchens", json=KITCHEN_PAYLOAD, headers=auth_headers)
    assert created.status_code == 201
    kitchen_id = created.json()["id"]

    await client.patch(
        f"/api/v1/kitchens/{kitchen_id}/branded-page",
        headers=auth_headers,
        json={"enabled": True, "tagline": "Discovery specials"},
    )

    resp = await client.get(
        "/api/v1/discovery/home",
        params={
            "latitude": KITCHEN_PAYLOAD["latitude"],
            "longitude": KITCHEN_PAYLOAD["longitude"],
            "max_km": 25,
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total_kitchens"] >= 1
    assert any(k["id"] == kitchen_id for k in data["near_you"])
    assert any(k["id"] == kitchen_id for k in data["featured"])
    featured = next(k for k in data["featured"] if k["id"] == kitchen_id)
    assert featured["tagline"] == "Discovery specials"
    assert "distance_km" in featured
