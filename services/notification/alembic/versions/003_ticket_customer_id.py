"""Bind support tickets to customer accounts for inbox."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_ticket_customer_id"
down_revision: Union[str, None] = "002_notifications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "support_tickets",
        sa.Column("customer_id", sa.UUID(), nullable=True),
        schema="ckac_support",
    )
    op.create_index(
        "ix_support_tickets_customer_id",
        "support_tickets",
        ["customer_id"],
        schema="ckac_support",
    )


def downgrade() -> None:
    op.drop_index("ix_support_tickets_customer_id", table_name="support_tickets", schema="ckac_support")
    op.drop_column("support_tickets", "customer_id", schema="ckac_support")
