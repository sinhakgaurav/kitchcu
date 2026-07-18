"""Kitchen Porter auto-book toggle + global/module flags.

Revision ID: 018
Revises: 017
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "018"
down_revision: Union[str, None] = "017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "kitchens",
        sa.Column(
            "porter_auto_book_enabled",
            sa.Boolean(),
            server_default="true",
            nullable=False,
        ),
        schema="ckac_identity",
    )
    op.add_column(
        "kitchens",
        sa.Column(
            "porter_auto_book_delay_min",
            sa.Integer(),
            server_default="15",
            nullable=False,
        ),
        schema="ckac_identity",
    )

    conn = op.get_bind()
    exists = conn.execute(
        sa.text("SELECT 1 FROM ckac_identity.feature_flags WHERE key = :k LIMIT 1"),
        {"k": "courier_porter_auto_book"},
    ).scalar()
    if not exists:
        conn.execute(
            sa.text(
                """
                INSERT INTO ckac_identity.feature_flags (key, enabled, scope, description)
                VALUES (
                    'courier_porter_auto_book',
                    true,
                    'delivery',
                    'Delayed Porter auto-book after order accept (default 15 min + retries)'
                )
                """
            )
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM ckac_identity.feature_flags WHERE key = :k"),
        {"k": "courier_porter_auto_book"},
    )
    op.drop_column("kitchens", "porter_auto_book_delay_min", schema="ckac_identity")
    op.drop_column("kitchens", "porter_auto_book_enabled", schema="ckac_identity")
