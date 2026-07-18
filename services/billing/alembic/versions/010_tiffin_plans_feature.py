"""Add tiffin_plans platform feature + Growth/Pro packages.

Revision ID: 010
Revises: 009
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FEATURE_KEY = "tiffin_plans"
MODULE_KEY = "tiffin_plans"


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO ckac_billing.platform_features
                (key, label, description, audience, module_key)
            VALUES (
                :key,
                'Tiffin / monthly plans',
                'Customer monthly thali/tiffin subscriptions — owner plans + accept/deny enrollments',
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
