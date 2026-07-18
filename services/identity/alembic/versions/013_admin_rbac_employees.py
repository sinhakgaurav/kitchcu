"""Admin RBAC permissions + role grants for platform employees."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PERMISSIONS = [
    ("employees:read", "List and view platform employees"),
    ("employees:write", "Create, update, deactivate employees and roles"),
    ("kitchens:read", "View kitchens and kitchen workspace"),
    ("kitchens:write", "Edit kitchen status, WhatsApp, modules"),
    ("packages:read", "View packages, features, plan mapping"),
    ("packages:write", "Edit packages and plan mapping"),
    ("marketing:read", "View kitchen marketing templates"),
    ("marketing:write", "Edit kitchen marketing templates (ops)"),
    ("api_keys:write", "Manage platform API keys"),
    ("refunds:write", "Manage refunds and money ops"),
    ("owners:write", "Override owner subscriptions"),
    ("tickets:write", "Handle support tickets"),
    ("streaming:read", "View kitchen live session status"),
]

ROLE_GRANTS = {
    "superadmin": ["*"],
    "ops": [
        "kitchens:read",
        "kitchens:write",
        "packages:read",
        "marketing:read",
        "marketing:write",
        "streaming:read",
        "owners:write",
    ],
    "support": [
        "kitchens:read",
        "marketing:read",
        "streaming:read",
        "tickets:write",
    ],
    "finance": [
        "packages:read",
        "packages:write",
        "refunds:write",
        "kitchens:read",
    ],
}


def upgrade() -> None:
    op.create_table(
        "admin_permissions",
        sa.Column("code", sa.String(64), primary_key=True),
        sa.Column("description", sa.String(255), nullable=False),
        schema="ckac_identity",
    )
    op.create_table(
        "admin_role_permissions",
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("permission_code", sa.String(64), nullable=False),
        sa.PrimaryKeyConstraint("role", "permission_code"),
        sa.ForeignKeyConstraint(
            ["permission_code"],
            ["ckac_identity.admin_permissions.code"],
            ondelete="CASCADE",
        ),
        schema="ckac_identity",
    )
    op.create_index(
        "ix_admin_role_permissions_role",
        "admin_role_permissions",
        ["role"],
        schema="ckac_identity",
    )

    perms = sa.table(
        "admin_permissions",
        sa.column("code", sa.String()),
        sa.column("description", sa.String()),
        schema="ckac_identity",
    )
    op.bulk_insert(perms, [{"code": c, "description": d} for c, d in PERMISSIONS])

    # Wildcard row for superadmin grants
    op.bulk_insert(perms, [{"code": "*", "description": "Full platform access"}])

    grants = sa.table(
        "admin_role_permissions",
        sa.column("role", sa.String()),
        sa.column("permission_code", sa.String()),
        schema="ckac_identity",
    )
    rows = []
    for role, codes in ROLE_GRANTS.items():
        for code in codes:
            rows.append({"role": role, "permission_code": code})
    op.bulk_insert(grants, rows)


def downgrade() -> None:
    op.drop_index("ix_admin_role_permissions_role", table_name="admin_role_permissions", schema="ckac_identity")
    op.drop_table("admin_role_permissions", schema="ckac_identity")
    op.drop_table("admin_permissions", schema="ckac_identity")
