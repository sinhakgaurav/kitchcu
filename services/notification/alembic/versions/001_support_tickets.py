"""Initial support ticketing schema."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS ckac_support")

    op.create_table(
        "support_tickets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("ticket_number", sa.String(32), nullable=False),
        sa.Column("audience", sa.String(16), nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), server_default="open", nullable=False),
        sa.Column("priority", sa.String(16), server_default="normal", nullable=False),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("customer_name", sa.String(255), nullable=True),
        sa.Column("customer_phone", sa.String(20), nullable=True),
        sa.Column("customer_email", sa.String(255), nullable=True),
        sa.Column("order_id", sa.UUID(), nullable=True),
        sa.Column("order_code", sa.String(64), nullable=True),
        sa.Column("kitchen_id", sa.UUID(), nullable=True),
        sa.Column("source", sa.String(20), server_default="ai_chat", nullable=False),
        sa.Column("assigned_admin_id", sa.UUID(), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticket_number", name="uq_support_ticket_number"),
        schema="ckac_support",
    )
    op.create_index("ix_support_tickets_status", "support_tickets", ["status"], schema="ckac_support")
    op.create_index("ix_support_tickets_order_id", "support_tickets", ["order_id"], schema="ckac_support")
    op.create_index("ix_support_tickets_kitchen_id", "support_tickets", ["kitchen_id"], schema="ckac_support")

    op.create_table(
        "support_ticket_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("ticket_id", sa.UUID(), nullable=False),
        sa.Column("author_type", sa.String(16), nullable=False),
        sa.Column("author_id", sa.UUID(), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("meta", sa.dialects.postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["ticket_id"], ["ckac_support.support_tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="ckac_support",
    )
    op.create_index(
        "ix_support_ticket_messages_ticket_id",
        "support_ticket_messages",
        ["ticket_id"],
        schema="ckac_support",
    )


def downgrade() -> None:
    op.drop_table("support_ticket_messages", schema="ckac_support")
    op.drop_table("support_tickets", schema="ckac_support")
