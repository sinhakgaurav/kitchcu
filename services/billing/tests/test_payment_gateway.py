"""Kitchen payment gateway credentials — owner configurable (TDD)."""

from tests.conftest import _seed_owner_with_order


async def test_owner_payment_gateway_get_empty_then_upsert(client):
    owner_id, kitchen_id, _order_id, _code, token = _seed_owner_with_order()
    headers = {"Authorization": f"Bearer {token}"}

    empty = await client.get(
        f"/api/v1/billing/kitchens/{kitchen_id}/payment-gateway",
        headers=headers,
    )
    assert empty.status_code == 200, empty.text
    body = empty.json()
    assert body["kitchen_id"] == str(kitchen_id)
    assert body["provider"] == "razorpay"
    assert body["key_secret_configured"] is False

    saved = await client.put(
        f"/api/v1/billing/kitchens/{kitchen_id}/payment-gateway",
        headers=headers,
        json={
            "key_id": "rzp_test_kitchen_abc",
            "key_secret": "kitchen_secret_value_9999",
            "webhook_secret": "whsec_kitchen_aaaa",
            "linked_account_id": "acc_test_linked",
            "is_active": True,
        },
    )
    assert saved.status_code == 200, saved.text
    out = saved.json()
    assert out["key_id"] == "rzp_test_kitchen_abc"
    assert out["key_secret_configured"] is True
    assert out["key_secret_masked"].endswith("9999")
    assert "kitchen_secret" not in (out["key_secret_masked"] or "")
    assert out["webhook_secret_configured"] is True
    assert out["linked_account_id"] == "acc_test_linked"

    # Omit secrets — keep existing
    keep = await client.put(
        f"/api/v1/billing/kitchens/{kitchen_id}/payment-gateway",
        headers=headers,
        json={"key_id": "rzp_test_kitchen_abc", "linked_account_id": "acc_test_linked_2"},
    )
    assert keep.status_code == 200
    assert keep.json()["key_secret_configured"] is True
    assert keep.json()["linked_account_id"] == "acc_test_linked_2"


async def test_owner_cannot_access_other_kitchen_gateway(client):
    _owner_a, kitchen_a, _, _, token_a = _seed_owner_with_order()
    _owner_b, kitchen_b, _, _, _token_b = _seed_owner_with_order()
    headers = {"Authorization": f"Bearer {token_a}"}
    res = await client.get(
        f"/api/v1/billing/kitchens/{kitchen_b}/payment-gateway",
        headers=headers,
    )
    assert res.status_code == 403
    _ = kitchen_a
