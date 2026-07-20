"""coupon_code + discount_amount on orders (F36 checkout apply).

Revision ID: 011
Revises: 010
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("coupon_code", sa.String(32), nullable=True),
        schema="ckac_orders",
    )
    op.add_column(
        "orders",
        sa.Column("discount_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
        schema="ckac_orders",
    )


def downgrade() -> None:
    op.drop_column("orders", "discount_amount", schema="ckac_orders")
    op.drop_column("orders", "coupon_code", schema="ckac_orders")
