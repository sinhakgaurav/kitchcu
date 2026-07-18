"""Add courier_status for Porter webhook sync.

Revision ID: 008
Revises: 007
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("courier_status", sa.String(64), nullable=True),
        schema="ckac_orders",
    )
    op.create_index(
        "ix_orders_courier_job_id",
        "orders",
        ["courier_job_id"],
        unique=False,
        schema="ckac_orders",
    )


def downgrade() -> None:
    op.drop_index("ix_orders_courier_job_id", table_name="orders", schema="ckac_orders")
    op.drop_column("orders", "courier_status", schema="ckac_orders")
