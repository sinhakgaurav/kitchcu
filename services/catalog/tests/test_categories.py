import pytest
from httpx import AsyncClient

from app.models import DEFAULT_CATEGORY_SLUGS


@pytest.mark.asyncio
async def test_list_categories_seeds_defaults(client: AsyncClient, kitchen_ctx):
    _, kitchen_id, token = kitchen_ctx
    response = await client.get(
        f"/api/v1/kitchens/{kitchen_id}/categories",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == len(DEFAULT_CATEGORY_SLUGS)
    slugs = {c["slug"] for c in data}
    assert "veg" in slugs
    assert "non_veg" in slugs


@pytest.mark.asyncio
async def test_categories_require_auth(client: AsyncClient, kitchen_ctx):
    _, kitchen_id, _ = kitchen_ctx
    response = await client.get(f"/api/v1/kitchens/{kitchen_id}/categories")
    assert response.status_code == 401
