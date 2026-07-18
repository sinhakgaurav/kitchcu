"""Owner WhatsApp / email marketing message templates."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "message_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("kitchen_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("subject", sa.String(255), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("variables", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        schema="ckac_marketing",
    )
    op.create_index(
        "ix_message_templates_kitchen",
        "message_templates",
        ["kitchen_id"],
        schema="ckac_marketing",
    )
    op.create_index(
        "ix_message_templates_kitchen_channel",
        "message_templates",
        ["kitchen_id", "channel"],
        schema="ckac_marketing",
    )


def downgrade() -> None:
    op.drop_index("ix_message_templates_kitchen_channel", table_name="message_templates", schema="ckac_marketing")
    op.drop_index("ix_message_templates_kitchen", table_name="message_templates", schema="ckac_marketing")
    op.drop_table("message_templates", schema="ckac_marketing")
