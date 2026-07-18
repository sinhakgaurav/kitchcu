"""Per-dish live showcase — prep / ingredients / prepared runtime state."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "live_sessions",
        sa.Column("dish_id", sa.UUID(), nullable=True),
        schema="ckac_streaming",
    )
    op.add_column(
        "live_sessions",
        sa.Column("dish_name", sa.String(255), nullable=True),
        schema="ckac_streaming",
    )
    op.add_column(
        "live_sessions",
        sa.Column(
            "showcase_phase",
            sa.String(20),
            server_default="idle",
            nullable=False,
        ),
        schema="ckac_streaming",
    )
    op.add_column(
        "live_sessions",
        sa.Column("active_prep_step_order", sa.Integer(), nullable=True),
        schema="ckac_streaming",
    )
    op.add_column(
        "live_sessions",
        sa.Column("prepared_at", sa.DateTime(timezone=True), nullable=True),
        schema="ckac_streaming",
    )
    op.add_column(
        "live_sessions",
        sa.Column(
            "showcase_snapshot",
            sa.dialects.postgresql.JSONB(),
            server_default="{}",
            nullable=False,
        ),
        schema="ckac_streaming",
    )
    op.create_index(
        "ix_live_sessions_dish_id",
        "live_sessions",
        ["dish_id"],
        schema="ckac_streaming",
    )


def downgrade() -> None:
    op.drop_index("ix_live_sessions_dish_id", table_name="live_sessions", schema="ckac_streaming")
    op.drop_column("live_sessions", "showcase_snapshot", schema="ckac_streaming")
    op.drop_column("live_sessions", "prepared_at", schema="ckac_streaming")
    op.drop_column("live_sessions", "active_prep_step_order", schema="ckac_streaming")
    op.drop_column("live_sessions", "showcase_phase", schema="ckac_streaming")
    op.drop_column("live_sessions", "dish_name", schema="ckac_streaming")
    op.drop_column("live_sessions", "dish_id", schema="ckac_streaming")
