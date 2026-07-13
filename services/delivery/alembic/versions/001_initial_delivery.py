"""Initial delivery schema — Sprint 13 (F27–F31)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS ckac_delivery")
    op.create_table(
        "delivery_quotes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("kitchen_id", sa.UUID(), nullable=False),
        sa.Column("customer_lat", sa.Numeric(9, 6), nullable=False),
        sa.Column("customer_lng", sa.Numeric(9, 6), nullable=False),
        sa.Column("distance_km", sa.Numeric(6, 2), nullable=False),
        sa.Column("fee", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("breakdown", sa.dialects.postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        schema="ckac_delivery",
    )
    op.create_index(
        "ix_delivery_quotes_kitchen",
        "delivery_quotes",
        ["kitchen_id"],
        schema="ckac_delivery",
    )


def downgrade() -> None:
    op.drop_table("delivery_quotes", schema="ckac_delivery")
