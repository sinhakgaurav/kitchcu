"""P52 customer checkup diet-report kill-switch + customer columns.

Revision ID: 028
Revises: 027
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "028"
down_revision: Union[str, None] = "027"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FLAG_KEY = "customer_diet_report"


def upgrade() -> None:
    op.add_column(
        "customers",
        sa.Column("diet_profile", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        schema="ckac_identity",
    )
    op.add_column(
        "customers",
        sa.Column(
            "diet_filter_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        schema="ckac_identity",
    )
    op.add_column(
        "customers",
        sa.Column("checkup_report_url", sa.Text(), nullable=True),
        schema="ckac_identity",
    )
    op.add_column(
        "customers",
        sa.Column("checkup_parsed_at", sa.DateTime(timezone=True), nullable=True),
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
                    'Customer checkup upload + ML diet filter for compatible kitchens'
                )
                """
            ),
            {"k": FLAG_KEY},
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM ckac_identity.feature_flags WHERE key = :k"),
        {"k": FLAG_KEY},
    )
    op.drop_column("customers", "checkup_parsed_at", schema="ckac_identity")
    op.drop_column("customers", "checkup_report_url", schema="ckac_identity")
    op.drop_column("customers", "diet_filter_enabled", schema="ckac_identity")
    op.drop_column("customers", "diet_profile", schema="ckac_identity")
