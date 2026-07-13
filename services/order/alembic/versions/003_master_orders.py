"""F06 multi-kitchen master orders."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "master_orders",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("master_order_code", sa.String(32), nullable=False),
        sa.Column("customer_id", sa.UUID(), nullable=False),
        sa.Column("customer_name", sa.String(255), nullable=False),
        sa.Column("customer_phone", sa.String(20), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("status", sa.String(24), server_default="created", nullable=False),
        sa.Column("payment_method", sa.String(16), nullable=False),
        sa.Column("currency", sa.String(3), server_default="INR", nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("delivery_fee", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("master_order_code", name="uq_master_orders_code"),
        sa.UniqueConstraint(
            "customer_id",
            "idempotency_key",
            name="uq_master_orders_customer_idempotency",
        ),
        schema="ckac_orders",
    )
    op.create_index(
        "ix_master_orders_customer_created",
        "master_orders",
        ["customer_id", sa.text("created_at DESC")],
        schema="ckac_orders",
    )
    op.add_column(
        "orders",
        sa.Column("master_order_id", sa.UUID(), nullable=True),
        schema="ckac_orders",
    )
    op.create_foreign_key(
        "fk_orders_master_order_id",
        "orders",
        "master_orders",
        ["master_order_id"],
        ["id"],
        source_schema="ckac_orders",
        referent_schema="ckac_orders",
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_orders_master_order_id",
        "orders",
        ["master_order_id"],
        schema="ckac_orders",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_orders_master_order_id",
        table_name="orders",
        schema="ckac_orders",
    )
    op.drop_constraint(
        "fk_orders_master_order_id",
        "orders",
        schema="ckac_orders",
        type_="foreignkey",
    )
    op.drop_column("orders", "master_order_id", schema="ckac_orders")
    op.drop_index(
        "ix_master_orders_customer_created",
        table_name="master_orders",
        schema="ckac_orders",
    )
    op.drop_table("master_orders", schema="ckac_orders")
