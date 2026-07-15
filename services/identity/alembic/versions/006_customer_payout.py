"""Customer payout profile — UPI, QR scanner, bank details for refunds."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_customer_payout"
down_revision: Union[str, None] = "005_delivery_fee_rules"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "customers",
        sa.Column("upi_vpa", sa.String(100), nullable=True),
        schema="ckac_identity",
    )
    op.add_column(
        "customers",
        sa.Column("upi_qr_url", sa.Text(), nullable=True),
        schema="ckac_identity",
    )
    op.add_column(
        "customers",
        sa.Column("bank_account_number", sa.String(34), nullable=True),
        schema="ckac_identity",
    )
    op.add_column(
        "customers",
        sa.Column("bank_ifsc", sa.String(11), nullable=True),
        schema="ckac_identity",
    )
    op.add_column(
        "customers",
        sa.Column("bank_account_name", sa.String(255), nullable=True),
        schema="ckac_identity",
    )


def downgrade() -> None:
    op.drop_column("customers", "bank_account_name", schema="ckac_identity")
    op.drop_column("customers", "bank_ifsc", schema="ckac_identity")
    op.drop_column("customers", "bank_account_number", schema="ckac_identity")
    op.drop_column("customers", "upi_qr_url", schema="ckac_identity")
    op.drop_column("customers", "upi_vpa", schema="ckac_identity")
