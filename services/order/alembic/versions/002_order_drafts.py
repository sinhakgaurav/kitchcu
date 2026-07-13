"""Order drafts for WhatsApp / message parsing (Sprint 4)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "order_drafts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("kitchen_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(20), server_default="draft", nullable=False),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("raw_message", sa.Text(), nullable=False),
        sa.Column("customer_phone", sa.String(20), nullable=True),
        sa.Column("parsed_items", JSONB(), server_default="[]"),
        sa.Column("unmatched_lines", JSONB(), server_default="[]"),
        sa.Column("special_notes", JSONB(), server_default="[]"),
        sa.Column("order_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["order_id"], ["ckac_orders.orders.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        schema="ckac_orders",
    )
    op.create_index(
        "ix_order_drafts_kitchen_status",
        "order_drafts",
        ["kitchen_id", "status"],
        schema="ckac_orders",
    )


def downgrade() -> None:
    op.drop_table("order_drafts", schema="ckac_orders")
