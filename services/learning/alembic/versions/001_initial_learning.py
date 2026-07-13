"""Initial learning schema — Sprint 16 (F21–F22)."""

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CURATED_SEED = [
    {
        "slug": "paneer-butter-masala",
        "title": "Paneer Butter Masala",
        "category": "north_indian",
        "cuisine": "north_indian",
        "description": "Creamy tomato gravy with soft paneer cubes — a cloud-kitchen staple.",
        "ingredients": ["paneer", "tomato", "butter", "cream", "kasuri methi"],
        "prep_steps": ["Blend tomato base", "Simmer with spices", "Add paneer and cream"],
        "image_url": "https://images.unsplash.com/photo-1631452180519-f014710f6fea?w=800&q=85&auto=format&fit=crop",
        "source_name": "kitchCU Curated",
    },
    {
        "slug": "masala-dosa",
        "title": "Masala Dosa",
        "category": "south_indian",
        "cuisine": "south_indian",
        "description": "Crisp fermented crepe with spiced potato filling.",
        "ingredients": ["rice batter", "urad dal", "potato", "mustard seeds", "curry leaves"],
        "prep_steps": ["Ferment batter overnight", "Spread on hot tawa", "Fill with masala"],
        "image_url": "https://images.unsplash.com/photo-1589301760014-d929f3979dbc?w=800&q=85&auto=format&fit=crop",
        "source_name": "kitchCU Curated",
    },
    {
        "slug": "veg-biryani",
        "title": "Veg Dum Biryani",
        "category": "north_indian",
        "cuisine": "north_indian",
        "description": "Layered basmati rice with vegetables and whole spices.",
        "ingredients": ["basmati rice", "mixed vegetables", "yogurt", "biryani masala", "saffron"],
        "prep_steps": ["Par-cook rice", "Layer with vegetables", "Dum on low heat"],
        "image_url": "https://images.unsplash.com/photo-1563379091339-03246963d96a?w=800&q=85&auto=format&fit=crop",
        "source_name": "kitchCU Curated",
    },
    {
        "slug": "gulab-jamun",
        "title": "Gulab Jamun",
        "category": "desserts",
        "cuisine": "north_indian",
        "description": "Soft khoya dumplings soaked in cardamom sugar syrup.",
        "ingredients": ["khoya", "maida", "sugar", "cardamom", "ghee"],
        "prep_steps": ["Knead dough", "Fry golden", "Soak in warm syrup"],
        "image_url": "https://images.unsplash.com/photo-1589119814766-f7650a8b7f0f?w=800&q=85&auto=format&fit=crop",
        "source_name": "kitchCU Curated",
    },
]


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS ckac_learning")

    op.create_table(
        "curated_recipes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("cuisine", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("ingredients", sa.dialects.postgresql.JSONB(), server_default="[]"),
        sa.Column("prep_steps", sa.dialects.postgresql.JSONB(), server_default="[]"),
        sa.Column("image_url", sa.String(2048), nullable=False),
        sa.Column("source_name", sa.String(255), nullable=False),
        sa.Column("source_url", sa.String(2048)),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
        schema="ckac_learning",
    )
    op.create_index("ix_curated_recipes_category", "curated_recipes", ["category"], schema="ckac_learning")

    op.create_table(
        "dish_trials",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("kitchen_id", sa.UUID(), nullable=False),
        sa.Column("curated_recipe_id", sa.UUID()),
        sa.Column("catalog_dish_id", sa.UUID(), nullable=False),
        sa.Column("dish_name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(30), server_default="draft", nullable=False),
        sa.Column("promo_type", sa.String(20), server_default="free", nullable=False),
        sa.Column("sample_price", sa.Numeric(10, 2)),
        sa.Column("rating_threshold", sa.Numeric(3, 2), server_default="4.0", nullable=False),
        sa.Column("avg_rating", sa.Numeric(3, 2)),
        sa.Column("invite_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("whatsapp_sent_at", sa.DateTime(timezone=True)),
        sa.Column("promoted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        schema="ckac_learning",
    )
    op.create_index("ix_dish_trials_kitchen", "dish_trials", ["kitchen_id"], schema="ckac_learning")

    op.create_table(
        "trial_invites",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("trial_id", sa.UUID(), nullable=False),
        sa.Column("customer_id", sa.UUID(), nullable=False),
        sa.Column("customer_phone", sa.String(20), nullable=False),
        sa.Column("customer_name", sa.String(255)),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        schema="ckac_learning",
    )
    op.create_index("ix_trial_invites_trial", "trial_invites", ["trial_id"], schema="ckac_learning")

    op.create_table(
        "trial_ratings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("trial_id", sa.UUID(), nullable=False),
        sa.Column("invite_id", sa.UUID(), nullable=False),
        sa.Column("home_taste_score", sa.Integer(), nullable=False),
        sa.Column("quality_score", sa.Integer(), nullable=False),
        sa.Column("feedback", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invite_id"),
        schema="ckac_learning",
    )
    op.create_index("ix_trial_ratings_trial", "trial_ratings", ["trial_id"], schema="ckac_learning")

    recipes = sa.table(
        "curated_recipes",
        sa.column("id", sa.UUID()),
        sa.column("title", sa.String()),
        sa.column("slug", sa.String()),
        sa.column("category", sa.String()),
        sa.column("cuisine", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("ingredients", sa.dialects.postgresql.JSONB()),
        sa.column("prep_steps", sa.dialects.postgresql.JSONB()),
        sa.column("image_url", sa.String()),
        sa.column("source_name", sa.String()),
        schema="ckac_learning",
    )
    op.bulk_insert(
        recipes,
        [{**row, "id": uuid.uuid4()} for row in CURATED_SEED],
    )


def downgrade() -> None:
    op.drop_table("trial_ratings", schema="ckac_learning")
    op.drop_table("trial_invites", schema="ckac_learning")
    op.drop_table("dish_trials", schema="ckac_learning")
    op.drop_table("curated_recipes", schema="ckac_learning")
