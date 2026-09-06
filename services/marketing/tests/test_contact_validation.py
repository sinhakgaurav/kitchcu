"""Shared contact validators applied to marketing intake (`ckac_common.validators`).

An owner pasting a blast list is the easiest way to smuggle an undeliverable
number into the platform, so template sends enforce the same phone rules as
owner registration.
"""

import pytest
from httpx import AsyncClient

from tests.conftest import _seed_marketing_ctx


async def _template_id(client: AsyncClient, ctx: dict) -> str:
    created = await client.post(
        f"/api/v1/kitchens/{ctx['kitchen_id']}/templates",
        headers={"Authorization": f"Bearer {ctx['owner_token']}"},
        json={
            "channel": "whatsapp",
            "name": "Contact validation blast",
            "body": "Hi {{ customer_name }} — today's specials are live.",
        },
    )
    assert created.status_code == 201, created.text
    return created.json()["id"]


@pytest.mark.parametrize(
    "raw",
    ["+919111111111", "919111111111", "9111111111", "0091 9111111111", "09111111111"],
)
@pytest.mark.asyncio
async def test_blast_phones_normalized_to_e164(client: AsyncClient, raw: str):
    ctx = _seed_marketing_ctx()
    template_id = await _template_id(client, ctx)
    res = await client.post(
        f"/api/v1/kitchens/{ctx['kitchen_id']}/templates/{template_id}/send",
        headers={"Authorization": f"Bearer {ctx['owner_token']}"},
        json={"audience": "phones", "phones": [raw], "dry_run": True},
    )
    assert res.status_code == 200, res.text
    assert res.json()["recipient_phones"] == ["+919111111111"]


@pytest.mark.parametrize(
    "raw",
    [
        "911111111111 1",  # 13 digits
        "91111111111",  # 11 digits
        "+14155552671",  # foreign country code
        "0123456789",  # leading 0 is not a mobile prefix
        "4111111111",  # leading 4 is not a mobile prefix
    ],
)
@pytest.mark.asyncio
async def test_blast_rejects_undeliverable_phone(client: AsyncClient, raw: str):
    ctx = _seed_marketing_ctx()
    template_id = await _template_id(client, ctx)
    res = await client.post(
        f"/api/v1/kitchens/{ctx['kitchen_id']}/templates/{template_id}/send",
        headers={"Authorization": f"Bearer {ctx['owner_token']}"},
        json={"audience": "phones", "phones": [raw], "dry_run": True},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_subscribe_name_keeps_machine_assigned_label(client: AsyncClient):
    """This only backfills the identity profile name, which is `Customer 0481`
    for OTP signups — so it takes display rules, not person-name rules."""
    ctx = _seed_marketing_ctx()
    plan = await client.post(
        f"/api/v1/kitchens/{ctx['kitchen_id']}/subscription-plans",
        headers={"Authorization": f"Bearer {ctx['owner_token']}"},
        json={
            "name": "Veg Thali Monthly",
            "plan_type": "thali",
            "price_monthly": 2499,
            "dishes_config": {
                "dish_ids": [str(ctx["dish_id"])],
                "weekdays": [0, 1, 2, 3, 4],
                "meals_per_day": 1,
            },
        },
    )
    assert plan.status_code == 201, plan.text
    res = await client.post(
        f"/api/v1/kitchens/{ctx['kitchen_id']}/subscription-plans/{plan.json()['id']}/subscribe",
        headers={"Authorization": f"Bearer {ctx['customer_token']}"},
        json={"customer_name": "  Customer 0481  "},
    )
    assert res.status_code == 201, res.text


@pytest.mark.asyncio
async def test_subscribe_rejects_overlong_name(client: AsyncClient):
    ctx = _seed_marketing_ctx()
    plan = await client.post(
        f"/api/v1/kitchens/{ctx['kitchen_id']}/subscription-plans",
        headers={"Authorization": f"Bearer {ctx['owner_token']}"},
        json={
            "name": "Veg Thali Monthly",
            "plan_type": "thali",
            "price_monthly": 2499,
            "dishes_config": {
                "dish_ids": [str(ctx["dish_id"])],
                "weekdays": [0, 1, 2, 3, 4],
                "meals_per_day": 1,
            },
        },
    )
    assert plan.status_code == 201, plan.text
    res = await client.post(
        f"/api/v1/kitchens/{ctx['kitchen_id']}/subscription-plans/{plan.json()['id']}/subscribe",
        headers={"Authorization": f"Bearer {ctx['customer_token']}"},
        json={"customer_name": "x" * 121},
    )
    assert res.status_code == 422
