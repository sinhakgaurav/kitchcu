"""Add dish delivery_time_min — Sprint 13 (F30)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_delivery_time"
down_revision: Union[str, None] = "003_cuisines"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "dishes",
        sa.Column("delivery_time_min", sa.Integer(), nullable=True),
        schema="ckac_catalog",
    )


def downgrade() -> None:
    op.drop_column("dishes", "delivery_time_min", schema="ckac_catalog")
