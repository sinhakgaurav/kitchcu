"""Drop the erroneous unique constraint on live_sessions.room_name.

room_name is derived deterministically from kitchen_id (`kitchcu-{kitchen_id.hex[:12]}`),
so a kitchen legitimately reuses the same room_name across every go-live/end cycle over
its lifetime. A global UNIQUE constraint made every go-live after a kitchen's first
ever session fail with a 500 (UniqueViolationError) — this migration replaces it with a
plain (non-unique) index for lookup performance.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "live_sessions_room_name_key", "live_sessions", schema="ckac_streaming", type_="unique"
    )
    op.create_index(
        "ix_live_sessions_room_name", "live_sessions", ["room_name"], schema="ckac_streaming"
    )


def downgrade() -> None:
    op.drop_index("ix_live_sessions_room_name", table_name="live_sessions", schema="ckac_streaming")
    op.create_unique_constraint(
        "live_sessions_room_name_key", "live_sessions", ["room_name"], schema="ckac_streaming"
    )
