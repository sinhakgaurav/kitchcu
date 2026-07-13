"""Add WhatsApp phone mapping to kitchens."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "kitchens",
        sa.Column("whatsapp_phone_id", sa.String(100), nullable=True),
        schema="ckac_identity",
    )
    op.create_index(
        "ix_kitchens_whatsapp_phone_id",
        "kitchens",
        ["whatsapp_phone_id"],
        unique=True,
        schema="ckac_identity",
    )


def downgrade() -> None:
    op.drop_index("ix_kitchens_whatsapp_phone_id", table_name="kitchens", schema="ckac_identity")
    op.drop_column("kitchens", "whatsapp_phone_id", schema="ckac_identity")
