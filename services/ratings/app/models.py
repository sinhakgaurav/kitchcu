import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Numeric, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from ckac_common.database import Base

MEDIA_TYPES = ("video", "audio")
MODERATION_STATUSES = ("approved", "reported", "rejected")
SUGGESTION_STATUSES = ("pending", "accepted", "rejected")


class DishRating(Base):
    __tablename__ = "dish_ratings"
    __table_args__ = (
        UniqueConstraint("order_id", "dish_id", "customer_id", name="uq_rating_order_dish_customer"),
        {"schema": "ckac_ratings"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    dish_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    home_taste_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    quality_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    media_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_type: Mapped[str | None] = mapped_column(String(10), nullable=True)
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified_purchase: Mapped[bool] = mapped_column(Boolean, default=True)
    moderation_status: Mapped[str] = mapped_column(String(20), default="approved")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class DishRatingAggregate(Base):
    __tablename__ = "dish_rating_aggregates"
    __table_args__ = (
        UniqueConstraint("dish_id", name="uq_aggregate_dish"),
        {"schema": "ckac_ratings"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    dish_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    rating_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_home_taste: Mapped[float] = mapped_column(Numeric(4, 2), default=0)
    avg_quality: Mapped[float] = mapped_column(Numeric(4, 2), default=0)
    overall_rating: Mapped[float] = mapped_column(Numeric(4, 2), default=0)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DishSuggestion(Base):
    __tablename__ = "dish_suggestions"
    __table_args__ = {"schema": "ckac_ratings"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    dish_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    suggestion_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    owner_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
