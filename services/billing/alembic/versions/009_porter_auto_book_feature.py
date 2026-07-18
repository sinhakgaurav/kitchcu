"""Add courier_porter_auto_book to platform features + Growth/Pro packages.

Revision ID: 009
Revises: 008
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FEATURE_KEY = "courier_porter_auto_book"
MODULE_KEY = "courier_porter_auto_book"


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO ckac_billing.platform_features
                (key, label, description, audience, module_key)
            VALUES (
                :key,
                'Porter auto-book',
                'Auto-book Porter ~15 min after accept for prep-ready pickup; retry until booked',
                'owner',
                :module_key
            )
            ON CONFLICT (key) DO NOTHING
            """
        ),
        {"key": FEATURE_KEY, "module_key": MODULE_KEY},
    )
    for code in ("growth", "pro"):
        conn.execute(
            sa.text(
                """
                INSERT INTO ckac_billing.package_features (package_id, feature_key)
                SELECT p.id, :fk
                FROM ckac_billing.packages p
                WHERE p.code = :code
                  AND NOT EXISTS (
                    SELECT 1 FROM ckac_billing.package_features pf
                    WHERE pf.package_id = p.id AND pf.feature_key = :fk
                  )
                """
            ),
            {"fk": FEATURE_KEY, "code": code},
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM ckac_billing.package_features WHERE feature_key = :fk"),
        {"fk": FEATURE_KEY},
    )
    conn.execute(
        sa.text("DELETE FROM ckac_billing.platform_features WHERE key = :k"),
        {"k": FEATURE_KEY},
    )
