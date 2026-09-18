"""Partial index for the live owner queue (open orders only).

Revision ID: 012
Revises: 011
"""

from typing import Sequence, Union

from alembic import op

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_orders_kitchen_open_created
        ON ckac_orders.orders (kitchen_id, created_at DESC)
        WHERE status NOT IN ('delivered', 'cancelled')
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ckac_orders.ix_orders_kitchen_open_created")
