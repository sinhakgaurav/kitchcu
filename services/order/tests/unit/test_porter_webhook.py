"""Porter webhook parsing (no DB)."""

from app.porter_webhook import extract_porter_job_and_status, normalize_porter_status, verify_porter_webhook_secret


def test_normalize_porter_status():
    assert normalize_porter_status("order_delivered") == "delivered"
    assert normalize_porter_status("IN_TRANSIT") == "in_transit"
    assert normalize_porter_status("rider-assigned") == "assigned"


def test_extract_nested_payload():
    job, status = extract_porter_job_and_status(
        {"data": {"order_id": "CRN123", "status": "picked_up"}}
    )
    assert job == "CRN123"
    assert status == "picked_up"


def test_webhook_secret_unset_allows():
    assert verify_porter_webhook_secret(None) is True
