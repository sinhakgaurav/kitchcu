"""Internal admin audit request schema — unit."""

import uuid

from app.internal_routes import InternalAdminAuditRequest


def test_internal_admin_audit_request_accepts_billing_payload():
    body = InternalAdminAuditRequest(
        actor_admin_id=uuid.uuid4(),
        actor_email="finance@kitchcu.dev",
        actor_role="finance",
        action="kitchen.package.assigned",
        resource_type="kitchen_package",
        resource_id=str(uuid.uuid4()),
        kitchen_id=uuid.uuid4(),
        summary="Package assigned",
        after={"package_code": "growth"},
    )
    assert body.action.startswith("kitchen.")
    assert body.after["package_code"] == "growth"
