import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ckac_common.database import Base

SUGGESTION_TYPES = (
    "seasonal",
    "dish_promo",
    "customer_winback",
    "combo_opportunity",
    "peak_staffing",
    "golden_performance_day",
)


class Suggestion(Base):
    __tablename__ = "suggestions"
    __table_args__ = {"schema": "ckac_growth"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    suggestion_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    action_payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class SeasonalPattern(Base):
    __tablename__ = "seasonal_patterns"
    __table_args__ = {"schema": "ckac_growth"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    region: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    season_event: Mapped[str] = mapped_column(String(100), nullable=False)
    dish_category: Mapped[str] = mapped_column(String(50), nullable=False)
    demand_multiplier: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)
    sample_dishes: Mapped[list] = mapped_column(JSONB, default=list)


class GoldenRecipePin(Base):
    """Pinned recipe/ingredient combo from a standout performance day."""

    __tablename__ = "golden_recipe_pins"
    __table_args__ = (
        UniqueConstraint(
            "kitchen_id",
            "dish_id",
            "performance_date",
            name="uq_golden_pin_kitchen_dish_day",
        ),
        {"schema": "ckac_growth"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    dish_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    suggestion_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    performance_date: Mapped[date] = mapped_column(Date, nullable=False)
    dish_name: Mapped[str] = mapped_column(String(255), nullable=False)
    recipe_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict)
    metrics: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
