"""Outbound notification models — F29/F45 (ckac_notifications)."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ckac_common.database import Base

TRACKING_ACTIVE_STATUSES = ("preparing", "out_for_delivery")


class NotificationLog(Base):
    __tablename__ = "notification_log"
    __table_args__ = {"schema": "ckac_notifications"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kitchen_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    recipient_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    template_id: Mapped[str] = mapped_column(String(100), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="queued")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class TrackingReminder(Base):
    __tablename__ = "tracking_reminders"
    __table_args__ = {"schema": "ckac_notifications"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    order_code: Mapped[str] = mapped_column(String(64), nullable=False)
    customer_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    tracking_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    order_status: Mapped[str] = mapped_column(String(32), nullable=False)
    interval_min: Mapped[int] = mapped_column(Integer, default=5)
    next_reminder_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
