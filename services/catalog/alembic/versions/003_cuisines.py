"""Add cuisines table and dish.cuisine_id — cuisine -> diet -> dish hierarchy."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "003_cuisines"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cuisines",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("kitchen_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(50), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.UniqueConstraint("kitchen_id", "slug", name="uq_cuisine_kitchen_slug"),
        schema="ckac_catalog",
    )
    op.add_column(
        "dishes",
        sa.Column("cuisine_id", UUID(as_uuid=True), nullable=True),
        schema="ckac_catalog",
    )
    op.create_foreign_key(
        "fk_dishes_cuisine_id",
        "dishes",
        "cuisines",
        ["cuisine_id"],
        ["id"],
        source_schema="ckac_catalog",
        referent_schema="ckac_catalog",
    )
    op.create_index(
        "ix_dishes_kitchen_cuisine",
        "dishes",
        ["kitchen_id", "cuisine_id"],
        schema="ckac_catalog",
    )


def downgrade() -> None:
    op.drop_index("ix_dishes_kitchen_cuisine", table_name="dishes", schema="ckac_catalog")
    op.drop_constraint("fk_dishes_cuisine_id", "dishes", schema="ckac_catalog", type_="foreignkey")
    op.drop_column("dishes", "cuisine_id", schema="ckac_catalog")
    op.drop_table("cuisines", schema="ckac_catalog")
