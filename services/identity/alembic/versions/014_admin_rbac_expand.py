"""Expand admin RBAC permissions for customers, flags, refunds:read."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_PERMS = [
    ("customers:read", "View customers"),
    ("customers:write", "Suspend customers / clear passwords"),
    ("flags:read", "View feature flags and journeys"),
    ("flags:write", "Toggle feature flags"),
    ("refunds:read", "View refunds, payments, settlements"),
]

EXTRA_GRANTS = {
    "superadmin": ["*"],  # already has *
    "ops": ["flags:read", "customers:read"],
    "support": ["customers:read", "customers:write"],
    "finance": ["refunds:read"],
}


def upgrade() -> None:
    conn = op.get_bind()
    for code, desc in NEW_PERMS:
        conn.execute(
            sa.text(
                """
                INSERT INTO ckac_identity.admin_permissions (code, description)
                VALUES (:c, :d)
                ON CONFLICT (code) DO NOTHING
                """
            ),
            {"c": code, "d": desc},
        )
    for role, perms in EXTRA_GRANTS.items():
        if role == "superadmin":
            continue
        for p in perms:
            conn.execute(
                sa.text(
                    """
                    INSERT INTO ckac_identity.admin_role_permissions (role, permission_code)
                    VALUES (:r, :p)
                    ON CONFLICT DO NOTHING
                    """
                ),
                {"r": role, "p": p},
            )


def downgrade() -> None:
    conn = op.get_bind()
    for role, perms in EXTRA_GRANTS.items():
        if role == "superadmin":
            continue
        for p in perms:
            conn.execute(
                sa.text(
                    "DELETE FROM ckac_identity.admin_role_permissions "
                    "WHERE role = :r AND permission_code = :p"
                ),
                {"r": role, "p": p},
            )
    for code, _ in NEW_PERMS:
        conn.execute(
            sa.text("DELETE FROM ckac_identity.admin_permissions WHERE code = :c"),
            {"c": code},
        )
