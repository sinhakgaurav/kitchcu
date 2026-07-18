"""Store Porter / platform courier job id on orders."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006_order_idempotency_key"  # noqa: matches revision id string
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("courier_partner", sa.String(32), nullable=True),
        schema="ckac_orders",
    )
    op.add_column(
        "orders",
        sa.Column("courier_job_id", sa.String(64), nullable=True),
        schema="ckac_orders",
    )


def downgrade() -> None:
    op.drop_column("orders", "courier_job_id", schema="ckac_orders")
    op.drop_column("orders", "courier_partner", schema="ckac_orders")
