import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ckac_common.database import Base

SESSION_STATUSES = ("live", "ended")
# Per-dish live cooking stages shown to customers during go-live.
SHOWCASE_PHASES = ("idle", "ingredients", "prep", "prepared")


class KitchenStreamSettings(Base):
    __tablename__ = "kitchen_stream_settings"
    __table_args__ = {"schema": "ckac_streaming"}

    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    live_sharing_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    q_and_a_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class LiveSession(Base):
    __tablename__ = "live_sessions"
    __table_args__ = {"schema": "ckac_streaming"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    # Not unique: room_name is derived deterministically from kitchen_id, so a kitchen
    # accumulates one row per go-live/end cycle over its lifetime and legitimately reuses
    # the same room_name across historical sessions.
    room_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="live", index=True)
    order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    dish_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    dish_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    showcase_phase: Mapped[str] = mapped_column(String(20), default="idle", nullable=False)
    active_prep_step_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prepared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    showcase_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict)
    viewer_count: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
