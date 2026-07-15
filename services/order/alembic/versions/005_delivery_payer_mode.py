"""Delivery mode/payer + customer coords for maps (owner vs customer logistics)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_delivery_payer_mode"
down_revision: Union[str, None] = "004_delivery_tracking"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("delivery_mode", sa.String(16), nullable=True),
        schema="ckac_orders",
    )
    op.add_column(
        "orders",
        sa.Column("delivery_payer", sa.String(16), nullable=True),
        schema="ckac_orders",
    )
    op.add_column(
        "orders",
        sa.Column("owner_delivery_cost", sa.Numeric(10, 2), server_default="0", nullable=False),
        schema="ckac_orders",
    )
    op.add_column(
        "orders",
        sa.Column("customer_latitude", sa.Float(), nullable=True),
        schema="ckac_orders",
    )
    op.add_column(
        "orders",
        sa.Column("customer_longitude", sa.Float(), nullable=True),
        schema="ckac_orders",
    )


def downgrade() -> None:
    op.drop_column("orders", "customer_longitude", schema="ckac_orders")
    op.drop_column("orders", "customer_latitude", schema="ckac_orders")
    op.drop_column("orders", "owner_delivery_cost", schema="ckac_orders")
    op.drop_column("orders", "delivery_payer", schema="ckac_orders")
    op.drop_column("orders", "delivery_mode", schema="ckac_orders")
