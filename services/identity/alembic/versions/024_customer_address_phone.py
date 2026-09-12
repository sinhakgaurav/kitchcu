"""Contact phone on each saved customer address.

Revision ID: 024
Revises: 023
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "024"
down_revision: Union[str, None] = "023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "customer_addresses",
        sa.Column("phone", sa.String(length=16), nullable=True),
        schema="ckac_identity",
    )
    op.execute(
        """
        UPDATE ckac_identity.customer_addresses AS a
        SET phone = c.phone
        FROM ckac_identity.customers AS c
        WHERE a.customer_id = c.id
          AND a.phone IS NULL
          AND c.phone IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_column("customer_addresses", "phone", schema="ckac_identity")
