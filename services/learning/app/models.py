import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ckac_common.database import Base

TRIAL_STATUSES = ("draft", "sampling", "collecting_ratings", "promoted", "archived")
PROMO_TYPES = ("free", "paid_sample")
INVITE_STATUSES = ("pending", "sent", "rated")


class CuratedRecipe(Base):
    __tablename__ = "curated_recipes"
    __table_args__ = {"schema": "ckac_learning"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    cuisine: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    ingredients: Mapped[list] = mapped_column(JSONB, default=list)
    prep_steps: Mapped[list] = mapped_column(JSONB, default=list)
    image_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(2048))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class DishTrial(Base):
    __tablename__ = "dish_trials"
    __table_args__ = {"schema": "ckac_learning"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    curated_recipe_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    catalog_dish_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    dish_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="draft")
    promo_type: Mapped[str] = mapped_column(String(20), default="free")
    sample_price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    rating_threshold: Mapped[float] = mapped_column(Numeric(3, 2), default=4.0)
    avg_rating: Mapped[float | None] = mapped_column(Numeric(3, 2))
    invite_count: Mapped[int] = mapped_column(Integer, default=0)
    whatsapp_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class TrialInvite(Base):
    __tablename__ = "trial_invites"
    __table_args__ = {"schema": "ckac_learning"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trial_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    customer_name: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class TrialRating(Base):
    __tablename__ = "trial_ratings"
    __table_args__ = {"schema": "ckac_learning"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trial_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    invite_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    home_taste_score: Mapped[int] = mapped_column(Integer, nullable=False)
    quality_score: Mapped[int] = mapped_column(Integer, nullable=False)
    feedback: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
