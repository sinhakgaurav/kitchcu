"""Customer profile photo + live-capture photo.

Revision ID: 025
Revises: 024
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "025"
down_revision: Union[str, None] = "024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FLAG_KEY = "customer_profile_photos"


def upgrade() -> None:
    op.add_column(
        "customers",
        sa.Column("live_photo_url", sa.Text(), nullable=True),
        schema="ckac_identity",
    )
    op.add_column(
        "customers",
        sa.Column("live_photo_captured_at", sa.DateTime(timezone=True), nullable=True),
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
                    'customer',
                    'Customer profile photo + live-capture photo uploads'
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
    op.drop_column("customers", "live_photo_captured_at", schema="ckac_identity")
    op.drop_column("customers", "live_photo_url", schema="ckac_identity")
