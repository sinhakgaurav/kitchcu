"""Package mapper — platform features → packages → owner/customer plans."""

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FEATURES = [
    ("whatsapp", "WhatsApp orders & CRM blasts", "owner", "whatsapp"),
    ("streaming", "Live kitchen go-live", "owner", "streaming"),
    ("livekit", "LiveKit media rooms", "owner", "livekit"),
    ("razorpay", "Kitchen Razorpay / Route", "owner", "razorpay"),
    ("refunds", "Refunds & disputes", "owner", "refunds"),
    ("marketing_broadcast", "WhatsApp/email marketing templates", "owner", "marketing_broadcast"),
    ("customer_checkout", "Customer PWA checkout", "both", "customer_checkout"),
    ("discovery", "Nearby kitchen discovery", "customer", None),
    ("ratings", "Home-taste ratings", "customer", None),
    ("loyalty_crm", "Owner CRM & coupons", "owner", None),
]

PACKAGES = [
    {
        "code": "starter",
        "name": "Starter",
        "audience": "owner",
        "description": "Core kitchen ops — menu, orders, WhatsApp intake",
        "features": ["whatsapp", "razorpay", "customer_checkout", "loyalty_crm"],
        "plan_tiers": ["starter", "trial"],
    },
    {
        "code": "growth",
        "name": "Growth",
        "audience": "owner",
        "description": "Marketing + ratings loop for scaling kitchens",
        "features": [
            "whatsapp",
            "razorpay",
            "customer_checkout",
            "loyalty_crm",
            "marketing_broadcast",
            "ratings",
            "refunds",
        ],
        "plan_tiers": ["growth"],
    },
    {
        "code": "pro",
        "name": "Pro",
        "audience": "owner",
        "description": "Live streaming + full growth stack",
        "features": [
            "whatsapp",
            "razorpay",
            "customer_checkout",
            "loyalty_crm",
            "marketing_broadcast",
            "ratings",
            "refunds",
            "streaming",
            "livekit",
            "discovery",
        ],
        "plan_tiers": ["pro", "enterprise"],
    },
    {
        "code": "customer_free",
        "name": "Customer free",
        "audience": "customer",
        "description": "Default customer experience on kitchCU",
        "features": ["customer_checkout", "discovery", "ratings"],
        "plan_tiers": [],
    },
]


def upgrade() -> None:
    op.create_table(
        "platform_features",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("audience", sa.String(20), nullable=False, server_default="owner"),
        sa.Column("module_key", sa.String(64), nullable=True),
        schema="ckac_billing",
    )
    op.create_table(
        "packages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("audience", sa.String(20), nullable=False, server_default="owner"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        schema="ckac_billing",
    )
    op.create_table(
        "package_features",
        sa.Column("package_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("feature_key", sa.String(64), nullable=False),
        sa.PrimaryKeyConstraint("package_id", "feature_key"),
        sa.ForeignKeyConstraint(["package_id"], ["ckac_billing.packages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["feature_key"], ["ckac_billing.platform_features.key"], ondelete="CASCADE"),
        schema="ckac_billing",
    )
    op.create_table(
        "plan_packages",
        sa.Column("plan_tier", sa.String(32), primary_key=True),
        sa.Column("package_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("audience", sa.String(20), nullable=False, server_default="owner"),
        sa.ForeignKeyConstraint(["package_id"], ["ckac_billing.packages.id"], ondelete="CASCADE"),
        schema="ckac_billing",
    )
    op.create_table(
        "kitchen_packages",
        sa.Column("kitchen_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("package_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["package_id"], ["ckac_billing.packages.id"], ondelete="RESTRICT"),
        schema="ckac_billing",
    )

    conn = op.get_bind()
    for key, label, audience, module_key in FEATURES:
        conn.execute(
            sa.text(
                """
                INSERT INTO ckac_billing.platform_features
                    (key, label, description, audience, module_key)
                VALUES (:key, :label, :label, :audience, :module_key)
                """
            ),
            {
                "key": key,
                "label": label,
                "audience": audience,
                "module_key": module_key,
            },
        )

    for pkg in PACKAGES:
        pkg_id = uuid.uuid4()
        conn.execute(
            sa.text(
                """
                INSERT INTO ckac_billing.packages
                    (id, code, name, audience, description, is_active)
                VALUES (:id, :code, :name, :audience, :description, true)
                """
            ),
            {
                "id": str(pkg_id),
                "code": pkg["code"],
                "name": pkg["name"],
                "audience": pkg["audience"],
                "description": pkg["description"],
            },
        )
        for fk in pkg["features"]:
            conn.execute(
                sa.text(
                    """
                    INSERT INTO ckac_billing.package_features (package_id, feature_key)
                    VALUES (:pid, :fk)
                    """
                ),
                {"pid": str(pkg_id), "fk": fk},
            )
        for tier in pkg["plan_tiers"]:
            conn.execute(
                sa.text(
                    """
                    INSERT INTO ckac_billing.plan_packages (plan_tier, package_id, audience)
                    VALUES (:tier, :pid, :audience)
                    """
                ),
                {"tier": tier, "pid": str(pkg_id), "audience": pkg["audience"]},
            )


def downgrade() -> None:
    op.drop_table("kitchen_packages", schema="ckac_billing")
    op.drop_table("plan_packages", schema="ckac_billing")
    op.drop_table("package_features", schema="ckac_billing")
    op.drop_table("packages", schema="ckac_billing")
    op.drop_table("platform_features", schema="ckac_billing")
