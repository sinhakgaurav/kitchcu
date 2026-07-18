"""Idempotency key on single-kitchen orders (money-path safety, mirrors master_orders)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_order_idempotency_key"
down_revision: Union[str, None] = "005_delivery_payer_mode"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("idempotency_key", sa.String(128), nullable=True),
        schema="ckac_orders",
    )
    # Partial unique index — only enforced when a key is supplied, so legacy rows
    # and owner-entered manual orders (no client-generated key) are unaffected.
    op.create_index(
        "uq_orders_kitchen_idempotency_key",
        "orders",
        ["kitchen_id", "idempotency_key"],
        unique=True,
        schema="ckac_orders",
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_orders_kitchen_idempotency_key",
        table_name="orders",
        schema="ckac_orders",
    )
    op.drop_column("orders", "idempotency_key", schema="ckac_orders")
