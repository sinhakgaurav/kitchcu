"""delivery_fee_payment: prepaid | pay_on_delivery for customer logistics share.

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


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("delivery_fee_payment", sa.String(32), nullable=True),
        schema="ckac_orders",
    )


def downgrade() -> None:
    op.drop_column("orders", "delivery_fee_payment", schema="ckac_orders")
