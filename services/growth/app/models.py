import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ckac_common.database import Base

SUGGESTION_TYPES = (
    "seasonal",
    "dish_promo",
    "customer_winback",
    "combo_opportunity",
    "peak_staffing",
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
