"""Initial growth schema — Sprint 12 (F09–F11, F39)."""

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SEASONAL_SEED = [
    ("india", "diwali", "seasonal_special", 1.45, ["Gulab Jamun", "Kaju Katli", "Samosa"]),
    ("india", "holi", "snacks", 1.30, ["Gujiya", "Thandai", "Pakora"]),
    ("india", "monsoon", "hot_drinks", 1.25, ["Masala Chai", "Soup", "Pakora"]),
    ("india", "summer", "cold_drinks", 1.35, ["Lassi", "Buttermilk", "Mango Shake"]),
    ("india", "winter", "hot_drinks", 1.20, ["Hot Chocolate", "Ginger Tea", "Soup"]),
]


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS ckac_growth")

    op.create_table(
        "suggestions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("kitchen_id", sa.UUID(), nullable=False),
        sa.Column("suggestion_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("action_payload", sa.dialects.postgresql.JSONB(), server_default="{}"),
        sa.Column("priority", sa.Integer(), server_default="0", nullable=False),
        sa.Column("dismissed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        schema="ckac_growth",
    )
    op.create_index("ix_suggestions_kitchen", "suggestions", ["kitchen_id"], schema="ckac_growth")

    op.create_table(
        "seasonal_patterns",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("region", sa.String(100), nullable=False),
        sa.Column("season_event", sa.String(100), nullable=False),
        sa.Column("dish_category", sa.String(50), nullable=False),
        sa.Column("demand_multiplier", sa.Numeric(4, 2), nullable=False),
        sa.Column("sample_dishes", sa.dialects.postgresql.JSONB(), server_default="[]"),
        sa.PrimaryKeyConstraint("id"),
        schema="ckac_growth",
    )
    op.create_index(
        "ix_seasonal_patterns_region",
        "seasonal_patterns",
        ["region"],
        schema="ckac_growth",
    )

    patterns = sa.table(
        "seasonal_patterns",
        sa.column("id", sa.UUID()),
        sa.column("region", sa.String()),
        sa.column("season_event", sa.String()),
        sa.column("dish_category", sa.String()),
        sa.column("demand_multiplier", sa.Numeric()),
        sa.column("sample_dishes", sa.dialects.postgresql.JSONB()),
        schema="ckac_growth",
    )
    op.bulk_insert(
        patterns,
        [
            {
                "id": uuid.uuid4(),
                "region": r,
                "season_event": e,
                "dish_category": c,
                "demand_multiplier": m,
                "sample_dishes": d,
            }
            for r, e, c, m, d in SEASONAL_SEED
        ],
    )


def downgrade() -> None:
    op.drop_table("seasonal_patterns", schema="ckac_growth")
    op.drop_table("suggestions", schema="ckac_growth")
