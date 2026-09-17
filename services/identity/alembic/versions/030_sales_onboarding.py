"""P55 sales role, kitchen onboard attribution, training playbook.

Revision ID: 030
Revises: 029
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "030"
down_revision: Union[str, None] = "029"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FLAG_KEY = "sales_onboarding"


def upgrade() -> None:
    op.add_column(
        "kitchens",
        sa.Column("onboarded_by_admin_id", UUID(as_uuid=True), nullable=True),
        schema="ckac_identity",
    )
    op.create_index(
        "ix_kitchens_onboarded_by_admin_id",
        "kitchens",
        ["onboarded_by_admin_id"],
        schema="ckac_identity",
    )
    op.create_table(
        "kitchen_training_progress",
        sa.Column("kitchen_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("step_key", sa.String(length=64), primary_key=True),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_by", UUID(as_uuid=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["kitchen_id"],
            ["ckac_identity.kitchens.id"],
            ondelete="CASCADE",
        ),
        schema="ckac_identity",
    )

    conn = op.get_bind()
    exists = conn.execute(
        sa.text("SELECT 1 FROM ckac_identity.feature_flags WHERE key = :k LIMIT 1"),
        {"k": FLAG_KEY},
    ).scalar()
    if not exists:
        conn.execute(
            sa.text(
                """
                INSERT INTO ckac_identity.feature_flags (key, enabled, scope, description)
                VALUES (
                    :k,
                    true,
                    'platform',
                    'Sales kitchen onboard + owner training playbook'
                )
                """
            ),
            {"k": FLAG_KEY},
        )

    conn.execute(
        sa.text(
            """
            INSERT INTO ckac_identity.admin_permissions (code, description)
            VALUES (
                'sales:write',
                'Onboard kitchens in the field and complete owner training'
            )
            ON CONFLICT (code) DO NOTHING
            """
        )
    )
    for role, perm in (("sales", "sales:write"), ("sales", "kitchens:read")):
        conn.execute(
            sa.text(
                """
                INSERT INTO ckac_identity.admin_role_permissions (role, permission_code)
                VALUES (:r, :p)
                ON CONFLICT DO NOTHING
                """
            ),
            {"r": role, "p": perm},
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "DELETE FROM ckac_identity.admin_role_permissions WHERE role = 'sales'"
        )
    )
    conn.execute(
        sa.text("DELETE FROM ckac_identity.admin_permissions WHERE code = 'sales:write'")
    )
    conn.execute(
        sa.text("DELETE FROM ckac_identity.feature_flags WHERE key = :k"),
        {"k": FLAG_KEY},
    )
    op.drop_table("kitchen_training_progress", schema="ckac_identity")
    op.drop_index(
        "ix_kitchens_onboarded_by_admin_id",
        table_name="kitchens",
        schema="ckac_identity",
    )
    op.drop_column("kitchens", "onboarded_by_admin_id", schema="ckac_identity")
