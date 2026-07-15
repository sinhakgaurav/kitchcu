"""F30 — owner-set max readiness time shown as customer-facing projection."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007_dish_max_time"
down_revision: Union[str, None] = "006_recipe_prep"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "dishes",
        sa.Column("max_time_min", sa.Integer(), nullable=True),
        schema="ckac_catalog",
    )
    # Backfill: max = prep + COALESCE(delivery, 0) — honest ceiling for existing dishes.
    op.execute(
        """
        UPDATE ckac_catalog.dishes
        SET max_time_min = prep_time_min + COALESCE(delivery_time_min, 0)
        WHERE max_time_min IS NULL
        """
    )
    op.alter_column("dishes", "max_time_min", nullable=False, schema="ckac_catalog")


def downgrade() -> None:
    op.drop_column("dishes", "max_time_min", schema="ckac_catalog")
