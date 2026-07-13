"""Initial identity schema: owners and kitchens."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geography

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS ckac_identity")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "owners",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("phone", sa.String(length=15), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("subscription_tier", sa.String(length=20), server_default="starter"),
        sa.Column("subscription_status", sa.String(length=20), server_default="trial"),
        sa.Column("subscription_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("phone"),
        schema="ckac_identity",
    )
    op.create_index("ix_ckac_identity_owners_phone", "owners", ["phone"], schema="ckac_identity")

    op.create_table(
        "kitchens",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(length=10), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("address_line", sa.Text(), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("pincode", sa.String(length=10), nullable=True),
        sa.Column("location", Geography(geometry_type="POINT", srid=4326), nullable=False),
        sa.Column("free_delivery_radius_km", sa.Float(), server_default="3.0"),
        sa.Column("max_delivery_radius_km", sa.Float(), server_default="10.0"),
        sa.Column("status", sa.String(length=20), server_default="pending_verification"),
        sa.Column("settings", sa.dialects.postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        schema="ckac_identity",
    )
    op.create_index("ix_ckac_identity_kitchens_owner", "kitchens", ["owner_id"], schema="ckac_identity")
    op.create_index("ix_ckac_identity_kitchens_code", "kitchens", ["code"], schema="ckac_identity")
    op.execute(
        "CREATE INDEX ix_ckac_identity_kitchens_location ON ckac_identity.kitchens USING GIST (location)"
    )


def downgrade() -> None:
    op.drop_table("kitchens", schema="ckac_identity")
    op.drop_table("owners", schema="ckac_identity")
