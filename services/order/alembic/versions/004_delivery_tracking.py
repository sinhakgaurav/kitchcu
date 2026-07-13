"""Add order delivery distance, fee accept, tracking — Sprint 13 (F28/F29/F31)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_delivery_tracking"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("distance_km", sa.Numeric(6, 2), nullable=True),
        schema="ckac_orders",
    )
    op.add_column(
        "orders",
        sa.Column("delivery_fee_accepted", sa.Boolean(), nullable=True),
        schema="ckac_orders",
    )
    op.add_column(
        "orders",
        sa.Column("tracking_token", sa.String(64), nullable=True),
        schema="ckac_orders",
    )
    op.create_index(
        "ix_orders_tracking_token",
        "orders",
        ["tracking_token"],
        unique=True,
        schema="ckac_orders",
    )


def downgrade() -> None:
    op.drop_index("ix_orders_tracking_token", table_name="orders", schema="ckac_orders")
    op.drop_column("orders", "tracking_token", schema="ckac_orders")
    op.drop_column("orders", "delivery_fee_accepted", schema="ckac_orders")
    op.drop_column("orders", "distance_km", schema="ckac_orders")
