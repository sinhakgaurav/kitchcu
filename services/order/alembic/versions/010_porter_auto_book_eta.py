"""Order ETA delivery fields + Porter auto-book schedule.

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


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("estimated_delivery_min", sa.Integer(), nullable=True),
        schema="ckac_orders",
    )
    op.add_column(
        "orders",
        sa.Column("estimated_delivery_at", sa.DateTime(timezone=True), nullable=True),
        schema="ckac_orders",
    )
    op.add_column(
        "orders",
        sa.Column("porter_auto_book_at", sa.DateTime(timezone=True), nullable=True),
        schema="ckac_orders",
    )
    op.add_column(
        "orders",
        sa.Column(
            "porter_auto_book_attempts",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        schema="ckac_orders",
    )
    op.add_column(
        "orders",
        sa.Column("porter_auto_book_last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        schema="ckac_orders",
    )
    op.create_index(
        "ix_orders_porter_auto_book_at",
        "orders",
        ["porter_auto_book_at"],
        unique=False,
        schema="ckac_orders",
    )


def downgrade() -> None:
    op.drop_index("ix_orders_porter_auto_book_at", table_name="orders", schema="ckac_orders")
    op.drop_column("orders", "porter_auto_book_last_attempt_at", schema="ckac_orders")
    op.drop_column("orders", "porter_auto_book_attempts", schema="ckac_orders")
    op.drop_column("orders", "porter_auto_book_at", schema="ckac_orders")
    op.drop_column("orders", "estimated_delivery_at", schema="ckac_orders")
    op.drop_column("orders", "estimated_delivery_min", schema="ckac_orders")
