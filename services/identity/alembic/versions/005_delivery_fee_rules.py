"""Add kitchen delivery fee rules — Sprint 13 (F27)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_delivery_fee_rules"
down_revision: Union[str, None] = "004_customers_oauth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "kitchens",
        sa.Column("delivery_fee_per_km", sa.Numeric(8, 2), server_default="10", nullable=False),
        schema="ckac_identity",
    )
    op.add_column(
        "kitchens",
        sa.Column("delivery_fee_flat_beyond", sa.Numeric(8, 2), server_default="0", nullable=False),
        schema="ckac_identity",
    )
    op.add_column(
        "kitchens",
        sa.Column("min_order_for_free_delivery", sa.Numeric(10, 2), nullable=True),
        schema="ckac_identity",
    )
    op.add_column(
        "kitchens",
        sa.Column("tracking_notify_interval_min", sa.Integer(), server_default="5", nullable=False),
        schema="ckac_identity",
    )


def downgrade() -> None:
    op.drop_column("kitchens", "tracking_notify_interval_min", schema="ckac_identity")
    op.drop_column("kitchens", "min_order_for_free_delivery", schema="ckac_identity")
    op.drop_column("kitchens", "delivery_fee_flat_beyond", schema="ckac_identity")
    op.drop_column("kitchens", "delivery_fee_per_km", schema="ckac_identity")
