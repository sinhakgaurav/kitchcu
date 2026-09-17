"""P54 dish calories / Healthy Control flags + kcal cap.

Revision ID: 029
Revises: 028
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "029"
down_revision: Union[str, None] = "028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FLAGS = (
    (
        "dish_calories",
        "Public dish calorie totals from pantry × recipe (kitchen estimate, not a lab label)",
    ),
    (
        "dish_healthy_tag",
        "Automatic Healthy badge when the plate meets the Control kcal cap and health-score floor",
    ),
)


def upgrade() -> None:
    op.create_table(
        "healthy_food_settings",
        sa.Column("id", sa.SmallInteger(), primary_key=True, server_default="1"),
        sa.Column("healthy_max_kcal", sa.Integer(), nullable=False, server_default="500"),
        sa.Column("healthy_min_score", sa.SmallInteger(), nullable=False, server_default="65"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_by", UUID(as_uuid=True), nullable=True),
        schema="ckac_identity",
    )
    op.execute(
        sa.text(
            """
            INSERT INTO ckac_identity.healthy_food_settings
              (id, healthy_max_kcal, healthy_min_score)
            VALUES (1, 500, 65)
            ON CONFLICT (id) DO NOTHING
            """
        )
    )

    conn = op.get_bind()
    for key, description in FLAGS:
        exists = conn.execute(
            sa.text("SELECT 1 FROM ckac_identity.feature_flags WHERE key = :k LIMIT 1"),
            {"k": key},
        ).scalar()
        if not exists:
            conn.execute(
                sa.text(
                    """
                    INSERT INTO ckac_identity.feature_flags (key, enabled, scope, description)
                    VALUES (:k, true, 'kitchen', :d)
                    """
                ),
                {"k": key, "d": description},
            )


def downgrade() -> None:
    conn = op.get_bind()
    for key, _desc in FLAGS:
        conn.execute(
            sa.text("DELETE FROM ckac_identity.feature_flags WHERE key = :k"),
            {"k": key},
        )
    op.drop_table("healthy_food_settings", schema="ckac_identity")
