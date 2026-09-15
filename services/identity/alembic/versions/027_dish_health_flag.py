"""P50 dish ingredient health kill-switch.

Revision ID: 027
Revises: 026
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "027"
down_revision: Union[str, None] = "026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FLAG_KEY = "dish_health"


def upgrade() -> None:
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
                    'kitchen',
                    'Customer ingredient health score + benefits/disadvantages from F19 recipes'
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
