"""Kitchen delivery subsidy percent for extended-range cost share."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "017"
down_revision: Union[str, None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "kitchens",
        sa.Column(
            "delivery_subsidy_percent",
            sa.Numeric(5, 2),
            server_default="50",
            nullable=False,
        ),
        schema="ckac_identity",
    )


def downgrade() -> None:
    op.drop_column("kitchens", "delivery_subsidy_percent", schema="ckac_identity")
