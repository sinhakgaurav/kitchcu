import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ckac_common.database import Base

ORDER_STATUSES = (
    "received",
    "accepted",
    "preparing",
    "ready",
    "out_for_delivery",
    "delivered",
    "cancelled",
)

TERMINAL_STATUSES = frozenset({"delivered", "cancelled"})

VALID_TRANSITIONS: dict[str, frozenset[str]] = {
    "received": frozenset({"accepted", "cancelled"}),
    "accepted": frozenset({"preparing", "cancelled"}),
    "preparing": frozenset({"ready", "cancelled"}),
    "ready": frozenset({"out_for_delivery", "delivered", "cancelled"}),
    "out_for_delivery": frozenset({"delivered", "cancelled"}),
    "delivered": frozenset(),
    "cancelled": frozenset(),
}


def can_transition(from_status: str, to_status: str) -> bool:
    return to_status in VALID_TRANSITIONS.get(from_status, frozenset())


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = {"schema": "ckac_orders"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    master_order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ckac_orders.master_orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    bill_id: Mapped[str] = mapped_column(String(32), nullable=False)
    order_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(32), default="received")
    source: Mapped[str] = mapped_column(String(32), default="manual")
    delivery_type: Mapped[str] = mapped_column(String(16), default="pickup")
    payment_method: Mapped[str] = mapped_column(String(16), default="cod")
    customer_name: Mapped[str | None] = mapped_column(String(255))
    customer_phone: Mapped[str | None] = mapped_column(String(20))
    subtotal: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    delivery_fee: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    distance_km: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    delivery_fee_accepted: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    delivery_mode: Mapped[str | None] = mapped_column(String(16), nullable=True)
    delivery_payer: Mapped[str | None] = mapped_column(String(16), nullable=True)
    owner_delivery_cost: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    customer_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    customer_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    tracking_token: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    estimated_prep_min: Mapped[int | None] = mapped_column(Integer)
    estimated_ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class MasterOrder(Base):
    __tablename__ = "master_orders"
    __table_args__ = {"schema": "ckac_orders"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    master_order_code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="created")
    payment_method: Mapped[str] = mapped_column(String(16), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    delivery_fee: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = {"schema": "ckac_orders"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ckac_orders.orders.id", ondelete="CASCADE"), nullable=False
    )
    dish_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    dish_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    special_instructions: Mapped[str | None] = mapped_column(Text)
    prep_time_min: Mapped[int] = mapped_column(Integer, default=30)


class OrderStatusEvent(Base):
    __tablename__ = "order_status_events"
    __table_args__ = {"schema": "ckac_orders"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ckac_orders.orders.id", ondelete="CASCADE"), nullable=False
    )
    from_status: Mapped[str | None] = mapped_column(String(32))
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class OrderDraft(Base):
    __tablename__ = "order_drafts"
    __table_args__ = {"schema": "ckac_orders"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    raw_message: Mapped[str] = mapped_column(Text, nullable=False)
    customer_phone: Mapped[str | None] = mapped_column(String(20))
    parsed_items: Mapped[list] = mapped_column(JSONB, default=list)
    unmatched_lines: Mapped[list] = mapped_column(JSONB, default=list)
    special_notes: Mapped[list] = mapped_column(JSONB, default=list)
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ckac_orders.orders.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
