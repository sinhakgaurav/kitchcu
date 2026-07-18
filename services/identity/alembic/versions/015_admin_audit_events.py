"""Platform admin audit event log."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "admin_audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_admin_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_email", sa.String(255), nullable=False),
        sa.Column("actor_role", sa.String(32), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(64), nullable=False),
        sa.Column("kitchen_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("summary", sa.String(500), nullable=False, server_default=""),
        sa.Column("before", postgresql.JSONB(), nullable=True),
        sa.Column("after", postgresql.JSONB(), nullable=True),
        sa.Column("correlation_id", sa.String(64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="ckac_identity",
    )
    op.create_index(
        "ix_admin_audit_created_at",
        "admin_audit_events",
        ["created_at"],
        schema="ckac_identity",
    )
    op.create_index(
        "ix_admin_audit_actor_created",
        "admin_audit_events",
        ["actor_admin_id", "created_at"],
        schema="ckac_identity",
    )
    op.create_index(
        "ix_admin_audit_resource",
        "admin_audit_events",
        ["resource_type", "resource_id", "created_at"],
        schema="ckac_identity",
    )
    op.create_index(
        "ix_admin_audit_kitchen_created",
        "admin_audit_events",
        ["kitchen_id", "created_at"],
        schema="ckac_identity",
        postgresql_where=sa.text("kitchen_id IS NOT NULL"),
    )

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO ckac_identity.admin_permissions (code, description)
            VALUES ('audit:read', 'View platform admin audit log')
            ON CONFLICT (code) DO NOTHING
            """
        )
    )
    for role in ("superadmin", "ops", "finance"):
        conn.execute(
            sa.text(
                """
                INSERT INTO ckac_identity.admin_role_permissions (role, permission_code)
                VALUES (:r, 'audit:read')
                ON CONFLICT (role, permission_code) DO NOTHING
                """
            ),
            {"r": role},
        )


def downgrade() -> None:
    op.drop_index("ix_admin_audit_kitchen_created", table_name="admin_audit_events", schema="ckac_identity")
    op.drop_index("ix_admin_audit_resource", table_name="admin_audit_events", schema="ckac_identity")
    op.drop_index("ix_admin_audit_actor_created", table_name="admin_audit_events", schema="ckac_identity")
    op.drop_index("ix_admin_audit_created_at", table_name="admin_audit_events", schema="ckac_identity")
    op.drop_table("admin_audit_events", schema="ckac_identity")
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM ckac_identity.admin_role_permissions WHERE permission_code = 'audit:read'")
    )
    conn.execute(
        sa.text("DELETE FROM ckac_identity.admin_permissions WHERE code = 'audit:read'")
    )
