import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_share_and_appreciate_recipe(client: AsyncClient, community_ctx):
    kid = community_ctx["kitchen_id"]
    owner_headers = {"Authorization": f"Bearer {community_ctx['owner_token']}"}
    customer_headers = {"Authorization": f"Bearer {community_ctx['customer_token']}"}

    shared = await client.post(
        f"/api/v1/kitchens/{kid}/community/recipes",
        json={
            "title": "Secret Paneer Masala",
            "summary": "Family recipe",
            "recipe_html": "<p>Marinate paneer overnight.</p>",
        },
        headers=owner_headers,
    )
    assert shared.status_code == 201
    body = shared.json()
    recipe_id = body["id"]
    assert body.get("cover_url") is None

    with_cover = await client.post(
        f"/api/v1/kitchens/{kid}/community/recipes",
        json={
            "title": "Covered Dal Tadka",
            "summary": "With photo",
            "recipe_html": "<p>Temper with jeera.</p>",
            "cover_url": "https://cdn.example/recipes/dal.jpg",
        },
        headers=owner_headers,
    )
    assert with_cover.status_code == 201
    assert with_cover.json()["cover_url"] == "https://cdn.example/recipes/dal.jpg"

    appreciated = await client.post(
        f"/api/v1/community/recipes/{recipe_id}/appreciate",
        headers=customer_headers,
    )
    assert appreciated.status_code == 200
    assert appreciated.json()["appreciation_count"] == 1

    rewards = await client.get(f"/api/v1/kitchens/{kid}/community/rewards", headers=owner_headers)
    assert rewards.status_code == 200
    assert rewards.json()["points_balance"] == 10


@pytest.mark.asyncio
async def test_redeem_subscription_discount(client: AsyncClient, community_ctx):
    kid = community_ctx["kitchen_id"]
    owner_headers = {"Authorization": f"Bearer {community_ctx['owner_token']}"}

    for _ in range(10):
        shared = await client.post(
            f"/api/v1/kitchens/{kid}/community/recipes",
            json={
                "title": "Recipe batch",
                "recipe_html": "<p>Step one</p>",
            },
            headers=owner_headers,
        )
        recipe_id = shared.json()["id"]
        await client.post(
            f"/api/v1/community/recipes/{recipe_id}/appreciate",
            headers={"Authorization": f"Bearer {community_ctx['customer_token']}"},
        )

    redeem = await client.post(
        f"/api/v1/kitchens/{kid}/community/rewards/redeem",
        json={"redemption_type": "subscription_discount"},
        headers=owner_headers,
    )
    assert redeem.status_code == 200
    assert redeem.json()["points_spent"] == 100
    assert redeem.json()["points_balance"] == 0


@pytest.mark.asyncio
async def test_compute_city_rankings(client: AsyncClient, community_ctx):
    kid = community_ctx["kitchen_id"]
    owner_headers = {"Authorization": f"Bearer {community_ctx['owner_token']}"}

    computed = await client.post(
        f"/api/v1/kitchens/{kid}/community/rankings/compute?scope=city&region_key=Pune",
        headers=owner_headers,
    )
    assert computed.status_code == 200
    body = computed.json()
    assert body["total"] >= 1
    assert body["rankings"][0]["kitchen_id"] == str(kid)

    listed = await client.get("/api/v1/community/rankings?scope=city&region_key=Pune")
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1


@pytest.mark.asyncio
async def test_public_recipes_skip_orphaned_kitchen(client: AsyncClient, community_ctx):
    import os
    import uuid as uuid_mod

    import psycopg2

    kid = community_ctx["kitchen_id"]
    owner_headers = {"Authorization": f"Bearer {community_ctx['owner_token']}"}
    kept = await client.post(
        f"/api/v1/kitchens/{kid}/community/recipes",
        json={"title": "Live Dal", "recipe_html": "<p>Boil.</p>"},
        headers=owner_headers,
    )
    assert kept.status_code == 201

    conn = psycopg2.connect(os.environ["DATABASE_SYNC_URL"])
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ckac_community.shared_recipes
            (id, kitchen_id, owner_id, title, recipe_html, status)
            VALUES (%s::uuid, %s::uuid, %s::uuid, 'Ghost Kitchen Recipe', '<p>x</p>', 'published')
            """,
            (str(uuid_mod.uuid4()), str(uuid_mod.uuid4()), str(uuid_mod.uuid4())),
        )
    conn.close()

    public = await client.get("/api/v1/community/recipes")
    assert public.status_code == 200, public.text
    titles = [r["title"] for r in public.json()["recipes"]]
    assert "Live Dal" in titles
    assert "Ghost Kitchen Recipe" not in titles
