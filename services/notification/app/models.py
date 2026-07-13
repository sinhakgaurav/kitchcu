"""Support ticketing models — customer complaints & AI chat escalations."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ckac_common.database import Base

TICKET_STATUSES = ("open", "in_progress", "waiting_customer", "resolved", "closed")
TICKET_PRIORITIES = ("low", "normal", "high", "urgent")
TICKET_CATEGORIES = (
    "order_issue",
    "delivery",
    "quality",
    "billing",
    "technical",
    "complaint",
    "general",
)
TICKET_SOURCES = ("ai_chat", "web_form", "admin")
AUTHOR_TYPES = ("customer", "admin", "system", "ai")


class SupportTicket(Base):
    __tablename__ = "support_tickets"
    __table_args__ = {"schema": "ckac_support"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    audience: Mapped[str] = mapped_column(String(16), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    priority: Mapped[str] = mapped_column(String(16), default="normal")
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    customer_name: Mapped[str | None] = mapped_column(String(255))
    customer_phone: Mapped[str | None] = mapped_column(String(20))
    customer_email: Mapped[str | None] = mapped_column(String(255))
    order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    order_code: Mapped[str | None] = mapped_column(String(64))
    kitchen_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    source: Mapped[str] = mapped_column(String(20), default="ai_chat")
    assigned_admin_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    resolution_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class SupportTicketMessage(Base):
    __tablename__ = "support_ticket_messages"
    __table_args__ = {"schema": "ckac_support"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ckac_support.support_tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_type: Mapped[str] = mapped_column(String(16), nullable=False)
    author_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    message: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
