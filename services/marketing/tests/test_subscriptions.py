"""F34/F35 tiffin monthly subscriptions — TDD."""

import uuid

import psycopg2
import pytest
from httpx import AsyncClient

from tests.conftest import SYNC_DB_URL, _make_customer_token, _make_owner_token, _seed_marketing_ctx


def _extra_customer(phone: str) -> uuid.UUID:
    cid = uuid.uuid4()
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ckac_identity.customers (id, phone, name, status)
            VALUES (%s::uuid, %s, 'Sub Customer', 'active')
            """,
            (str(cid), phone),
        )
    conn.close()
    return cid


def _plan_body(ctx: dict, **overrides) -> dict:
    body = {
        "name": "Veg Thali Monthly",
        "plan_type": "thali",
        "price_monthly": 2499,
        "dishes_config": {
            "dish_ids": [str(ctx["dish_id"])],
            "weekdays": [0, 1, 2, 3, 4],
            "meals_per_day": 1,
        },
    }
    body.update(overrides)
    return body


@pytest.mark.asyncio
async def test_owner_plan_crud_and_accept_deny_flow(client: AsyncClient):
    ctx = _seed_marketing_ctx()
    kitchen_id = ctx["kitchen_id"]
    owner_headers = {"Authorization": f"Bearer {ctx['owner_token']}"}
    customer_headers = {"Authorization": f"Bearer {ctx['customer_token']}"}

    create = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/subscription-plans",
        headers=owner_headers,
        json=_plan_body(ctx),
    )
    assert create.status_code == 201, create.text
    plan = create.json()
    assert plan["name"] == "Veg Thali Monthly"
    assert plan["is_active"] is True
    plan_id = plan["id"]

    pub = await client.get(f"/api/v1/kitchens/{kitchen_id}/subscription-plans/public")
    assert pub.status_code == 200
    assert pub.json()["total"] == 1

    req = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/subscription-plans/{plan_id}/subscribe",
        headers=customer_headers,
        json={"customer_name": "Asha"},
    )
    assert req.status_code == 201, req.text
    sub = req.json()
    assert sub["status"] == "pending"
    sub_id = sub["id"]

    listed = await client.get(
        f"/api/v1/kitchens/{kitchen_id}/subscriptions?status=pending",
        headers=owner_headers,
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    accept = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/subscriptions/{sub_id}/accept",
        headers=owner_headers,
        json={"owner_note": "Welcome"},
    )
    assert accept.status_code == 200, accept.text
    assert accept.json()["status"] == "active"

    pause = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/subscriptions/{sub_id}/deactivate",
        headers=owner_headers,
        json={},
    )
    assert pause.status_code == 200
    assert pause.json()["status"] == "paused"

    resume = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/subscriptions/{sub_id}/activate",
        headers=owner_headers,
        json={},
    )
    assert resume.status_code == 200
    assert resume.json()["status"] == "active"

    summary = await client.get(
        f"/api/v1/kitchens/{kitchen_id}/subscriptions/summary",
        headers=owner_headers,
    )
    assert summary.status_code == 200
    body = summary.json()
    assert body["active"] == 1
    assert body["mrr_estimate"] == 2499.0

    deactivate_plan = await client.patch(
        f"/api/v1/kitchens/{kitchen_id}/subscription-plans/{plan_id}",
        headers=owner_headers,
        json={"is_active": False},
    )
    assert deactivate_plan.status_code == 200
    assert deactivate_plan.json()["is_active"] is False


@pytest.mark.asyncio
async def test_combo_and_single_dish_plan_rules(client: AsyncClient):
    ctx = _seed_marketing_ctx()
    kitchen_id = ctx["kitchen_id"]
    owner_headers = {"Authorization": f"Bearer {ctx['owner_token']}"}

    bad_combo = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/subscription-plans",
        headers=owner_headers,
        json=_plan_body(ctx, name="Tiny Combo", plan_type="combo"),
    )
    assert bad_combo.status_code == 400
    assert "two" in bad_combo.json()["detail"].lower()

    combo = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/subscription-plans",
        headers=owner_headers,
        json=_plan_body(
            ctx,
            name="Lunch Combo",
            plan_type="combo",
            price_monthly=2999,
            dishes_config={
                "dish_ids": [str(ctx["dish_id"]), str(ctx["dish_id_2"])],
                "weekdays": [0, 1, 2, 3, 4],
                "meals_per_day": 1,
            },
        ),
    )
    assert combo.status_code == 201, combo.text
    assert len(combo.json()["dishes_config"]["dish_ids"]) == 2

    bad_single = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/subscription-plans",
        headers=owner_headers,
        json=_plan_body(
            ctx,
            name="Bad Single",
            plan_type="single_dish",
            dishes_config={
                "dish_ids": [str(ctx["dish_id"]), str(ctx["dish_id_2"])],
                "weekdays": [0, 1, 2, 3, 4],
                "meals_per_day": 1,
            },
        ),
    )
    assert bad_single.status_code == 400

    single = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/subscription-plans",
        headers=owner_headers,
        json=_plan_body(
            ctx,
            name="Paneer Monthly",
            plan_type="single_dish",
            price_monthly=999,
        ),
    )
    assert single.status_code == 201, single.text
    assert single.json()["plan_type"] == "single_dish"


@pytest.mark.asyncio
async def test_owner_deny_pending_subscription(client: AsyncClient):
    ctx = _seed_marketing_ctx()
    kitchen_id = ctx["kitchen_id"]
    owner_headers = {"Authorization": f"Bearer {ctx['owner_token']}"}
    customer_headers = {"Authorization": f"Bearer {ctx['customer_token']}"}

    plan = (
        await client.post(
            f"/api/v1/kitchens/{kitchen_id}/subscription-plans",
            headers=owner_headers,
            json=_plan_body(ctx, name="Lunch Tiffin", plan_type="tiffin", price_monthly=1999),
        )
    ).json()
    sub = (
        await client.post(
            f"/api/v1/kitchens/{kitchen_id}/subscription-plans/{plan['id']}/subscribe",
            headers=customer_headers,
            json={},
        )
    ).json()

    deny = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/subscriptions/{sub['id']}/deny",
        headers=owner_headers,
        json={"owner_note": "Capacity full"},
    )
    assert deny.status_code == 200
    assert deny.json()["status"] == "denied"


@pytest.mark.asyncio
async def test_customer_cancel_subscription(client: AsyncClient):
    ctx = _seed_marketing_ctx()
    kitchen_id = ctx["kitchen_id"]
    owner_headers = {"Authorization": f"Bearer {ctx['owner_token']}"}
    customer_headers = {"Authorization": f"Bearer {ctx['customer_token']}"}

    plan = (
        await client.post(
            f"/api/v1/kitchens/{kitchen_id}/subscription-plans",
            headers=owner_headers,
            json=_plan_body(
                ctx,
                name="Combo Box",
                plan_type="combo",
                price_monthly=2999,
                dishes_config={
                    "dish_ids": [str(ctx["dish_id"]), str(ctx["dish_id_2"])],
                    "weekdays": [0, 1, 2, 3, 4],
                    "meals_per_day": 1,
                },
            ),
        )
    ).json()
    sub = (
        await client.post(
            f"/api/v1/kitchens/{kitchen_id}/subscription-plans/{plan['id']}/subscribe",
            headers=customer_headers,
            json={},
        )
    ).json()
    await client.post(
        f"/api/v1/kitchens/{kitchen_id}/subscriptions/{sub['id']}/accept",
        headers=owner_headers,
        json={},
    )

    cancel = await client.post(
        f"/api/v1/customers/me/subscriptions/{sub['id']}/cancel",
        headers=customer_headers,
    )
    assert cancel.status_code == 200, cancel.text
    assert cancel.json()["status"] == "cancelled"

    mine = await client.get("/api/v1/customers/me/subscriptions", headers=customer_headers)
    assert mine.status_code == 200
    assert mine.json()["total"] >= 1


@pytest.mark.asyncio
async def test_duplicate_open_subscription_rejected(client: AsyncClient):
    ctx = _seed_marketing_ctx()
    kitchen_id = ctx["kitchen_id"]
    owner_headers = {"Authorization": f"Bearer {ctx['owner_token']}"}
    customer_headers = {"Authorization": f"Bearer {ctx['customer_token']}"}

    plan = (
        await client.post(
            f"/api/v1/kitchens/{kitchen_id}/subscription-plans",
            headers=owner_headers,
            json=_plan_body(
                ctx,
                name="Single Dish Pack",
                plan_type="single_dish",
                price_monthly=999,
            ),
        )
    ).json()
    first = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/subscription-plans/{plan['id']}/subscribe",
        headers=customer_headers,
        json={},
    )
    assert first.status_code == 201
    second = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/subscription-plans/{plan['id']}/subscribe",
        headers=customer_headers,
        json={},
    )
    assert second.status_code == 400
    _ = _make_owner_token
    _ = _make_customer_token
    _ = _extra_customer
