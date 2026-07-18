"""Admin audit helpers — unit (no DB)."""

from app.admin_audit import AdminAuditEventRow
import uuid
from datetime import UTC, datetime


def test_audit_event_row_accepts_masked_payload():
    row = AdminAuditEventRow(
        id=uuid.uuid4(),
        actor_admin_id=uuid.uuid4(),
        actor_email="ops@kitchcu.dev",
        actor_role="ops",
        action="kitchen.status.updated",
        resource_type="kitchen",
        resource_id=str(uuid.uuid4()),
        kitchen_id=uuid.uuid4(),
        summary="Kitchen CKPNQ001 status active → suspended",
        before={"status": "active"},
        after={"status": "suspended"},
        correlation_id="corr-1",
        created_at=datetime.now(UTC),
    )
    assert "suspended" in row.summary
    assert row.before == {"status": "active"}


def test_audit_event_row_allows_null_secrets_fields():
    row = AdminAuditEventRow(
        id=uuid.uuid4(),
        actor_admin_id=None,
        actor_email="admin@kitchcu.dev",
        actor_role="superadmin",
        action="platform_api_key.updated",
        resource_type="api_key",
        resource_id="meta_app_secret",
        summary="API key slot configured",
        before=None,
        after={"configured": True},
        correlation_id=None,
        created_at=datetime.now(UTC),
    )
    assert row.after["configured"] is True
