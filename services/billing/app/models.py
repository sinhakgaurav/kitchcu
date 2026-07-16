import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ckac_common.database import Base

PAYMENT_STATUSES = (
    "created",
    "pending",
    "authorized",
    "captured",
    "partially_refunded",
    "failed",
    "refunded",
)
PAYMENT_METHODS = ("online", "upi", "cod")
SUBSCRIPTION_STATUSES = ("trial", "active", "past_due", "cancelled")
REFUND_KINDS = ("full", "partial")
REFUND_CHANNELS = ("gateway", "direct_transfer")
REFUND_STATUSES = ("requested", "processing", "completed", "failed")
REFUND_DESTINATION_TYPES = ("upi", "bank", "gateway_original")


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint("order_id", "method", name="uq_payment_order_method"),
        {"schema": "ckac_billing"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    master_order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    kitchen_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    method: Mapped[str] = mapped_column(String(20), nullable=False)
    razorpay_order_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    razorpay_payment_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="created")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Refund(Base):
    __tablename__ = "refunds"
    __table_args__ = {"schema": "ckac_billing"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    status: Mapped[str] = mapped_column(String(20), default="requested")
    destination_type: Mapped[str] = mapped_column(String(32), nullable=False)
    destination_upi: Mapped[str | None] = mapped_column(String(100), nullable=True)
    destination_bank_account: Mapped[str | None] = mapped_column(String(34), nullable=True)
    destination_bank_ifsc: Mapped[str | None] = mapped_column(String(11), nullable=True)
    destination_account_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    transfer_remark: Mapped[str] = mapped_column(String(128), nullable=False)
    razorpay_refund_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    evidence_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Settlement(Base):
    __tablename__ = "settlements"
    __table_args__ = (
        UniqueConstraint("order_id", name="uq_settlements_order_id"),
        {"schema": "ckac_billing"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    master_order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    payment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    gross_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    delivery_fee_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    platform_fee: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    net_to_owner: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    razorpay_transfer_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    settlement_status: Mapped[str] = mapped_column(String(20), default="pending")
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class KitchenPaymentGateway(Base):
    __tablename__ = "kitchen_payment_gateways"
    __table_args__ = (
        UniqueConstraint("kitchen_id", "provider", name="uq_kitchen_payment_gateway_provider"),
        {"schema": "ckac_billing"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(32), default="razorpay")
    key_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    key_secret_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    webhook_secret_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    linked_account_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OwnerSubscription(Base):
    __tablename__ = "owner_subscriptions"
    __table_args__ = {"schema": "ckac_billing"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    plan_tier: Mapped[str] = mapped_column(String(20), nullable=False)
    billing_cycle: Mapped[str] = mapped_column(String(10), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    razorpay_subscription_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="trial")
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class KitchenMessagingWallet(Base):
    __tablename__ = "kitchen_messaging_wallets"
    __table_args__ = {"schema": "ckac_billing"}

    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    balance_inr: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    low_balance_alerted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class SubscriptionLedgerEntry(Base):
    __tablename__ = "subscription_ledger_entries"
    __table_args__ = {"schema": "ckac_billing"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    kitchen_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    platform_revenue_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    wallet_credit_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class KitchenGstProfile(Base):
    __tablename__ = "kitchen_gst_profiles"
    __table_args__ = (
        UniqueConstraint("kitchen_id", name="uq_kitchen_gst_profiles_kitchen"),
        UniqueConstraint("gstin", name="uq_kitchen_gst_profiles_gstin"),
        {"schema": "ckac_billing"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    gstin: Mapped[str] = mapped_column(String(15), nullable=False)
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    trade_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    state_code: Mapped[str] = mapped_column(String(2), nullable=False)
    registered_address: Mapped[str] = mapped_column(Text, nullable=False)
    default_tax_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=5.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    invoice_prefix: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GstTaxInvoice(Base):
    __tablename__ = "gst_tax_invoices"
    __table_args__ = (
        UniqueConstraint("order_id", name="uq_gst_tax_invoices_order"),
        UniqueConstraint("invoice_number", name="uq_gst_tax_invoices_number"),
        {"schema": "ckac_billing"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    invoice_number: Mapped[str] = mapped_column(String(64), nullable=False)
    invoice_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    order_code: Mapped[str] = mapped_column(String(64), nullable=False)
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    place_of_supply_state_code: Mapped[str] = mapped_column(String(2), nullable=False)
    supply_type: Mapped[str] = mapped_column(String(16), default="intra_state")
    taxable_value: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    cgst_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    sgst_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    igst_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    tax_rate: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    gross_total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class GstMonthlyAudit(Base):
    __tablename__ = "gst_monthly_audits"
    __table_args__ = (
        UniqueConstraint(
            "kitchen_id",
            "period_year",
            "period_month",
            name="uq_gst_monthly_audits_period",
        ),
        {"schema": "ckac_billing"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    period_year: Mapped[int] = mapped_column(Integer, nullable=False)
    period_month: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="open")
    invoice_count: Mapped[int] = mapped_column(Integer, default=0)
    total_taxable: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    total_cgst: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    total_sgst: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    total_igst: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    total_tax: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    total_gross_sales: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by_owner_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    balance_sheet_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
