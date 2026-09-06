"""Customer notification preferences (order updates, offers, channel).

Revision ID: 023
Revises: 022
Create Date: 2026-09-06
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "023"
down_revision: Union[str, None] = "022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Transactional updates stay on by default; marketing stays off until the
    # customer opts in.
    op.add_column(
        "customers",
        sa.Column(
            "notify_order_updates", sa.Boolean(), nullable=False, server_default="true"
        ),
        schema="ckac_identity",
    )
    op.add_column(
        "customers",
        sa.Column("notify_offers", sa.Boolean(), nullable=False, server_default="false"),
        schema="ckac_identity",
    )
    op.add_column(
        "customers",
        sa.Column(
            "notify_channel",
            sa.String(length=16),
            nullable=False,
            server_default="whatsapp",
        ),
        schema="ckac_identity",
    )


def downgrade() -> None:
    op.drop_column("customers", "notify_channel", schema="ckac_identity")
    op.drop_column("customers", "notify_offers", schema="ckac_identity")
    op.drop_column("customers", "notify_order_updates", schema="ckac_identity")
