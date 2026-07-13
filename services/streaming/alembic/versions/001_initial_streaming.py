"""Initial streaming schema — Sprint 18 (F46–F48)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS ckac_streaming")

    op.create_table(
        "kitchen_stream_settings",
        sa.Column("kitchen_id", sa.UUID(), nullable=False),
        sa.Column("live_sharing_enabled", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("q_and_a_enabled", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("kitchen_id"),
        schema="ckac_streaming",
    )

    op.create_table(
        "live_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("kitchen_id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("room_name", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), server_default="live", nullable=False),
        sa.Column("order_id", sa.UUID()),
        sa.Column("viewer_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("notes", sa.Text()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("room_name"),
        schema="ckac_streaming",
    )
    op.create_index("ix_live_sessions_kitchen", "live_sessions", ["kitchen_id"], schema="ckac_streaming")
    op.create_index("ix_live_sessions_status", "live_sessions", ["status"], schema="ckac_streaming")


def downgrade() -> None:
    op.drop_table("live_sessions", schema="ckac_streaming")
    op.drop_table("kitchen_stream_settings", schema="ckac_streaming")
