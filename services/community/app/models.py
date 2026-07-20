import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ckac_common.database import Base

POINTS_PER_APPRECIATION = 10
SUBSCRIPTION_DISCOUNT_COST = 100
FEATURED_LISTING_COST = 500


class SharedRecipe(Base):
    __tablename__ = "shared_recipes"
    __table_args__ = {"schema": "ckac_community"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    recipe_html: Mapped[str] = mapped_column(Text, nullable=False)
    cover_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    dish_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    status: Mapped[str] = mapped_column(String(20), default="published")
    appreciation_count: Mapped[int] = mapped_column(Integer, default=0)
    points_earned: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class RecipeAppreciation(Base):
    __tablename__ = "recipe_appreciations"
    __table_args__ = (
        UniqueConstraint("recipe_id", "customer_id", name="uq_recipe_appreciation_customer"),
        {"schema": "ckac_community"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class KitchenRewardBalance(Base):
    __tablename__ = "kitchen_reward_balances"
    __table_args__ = {"schema": "ckac_community"}

    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    points_balance: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class RewardPointLedger(Base):
    __tablename__ = "reward_point_ledger"
    __table_args__ = {"schema": "ckac_community"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    delta: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(50), nullable=False)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class RewardRedemption(Base):
    __tablename__ = "reward_redemptions"
    __table_args__ = {"schema": "ckac_community"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    redemption_type: Mapped[str] = mapped_column(String(30), nullable=False)
    points_spent: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class ChefRanking(Base):
    __tablename__ = "chef_rankings"
    __table_args__ = (
        UniqueConstraint("period", "scope", "region_key", "kitchen_id", name="uq_chef_ranking_period"),
        {"schema": "ckac_community"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    period: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    scope: Mapped[str] = mapped_column(String(20), nullable=False)
    region_key: Mapped[str] = mapped_column(String(100), nullable=False)
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    kitchen_code: Mapped[str] = mapped_column(String(20), nullable=False)
    kitchen_name: Mapped[str] = mapped_column(String(255), nullable=False)
    score: Mapped[float] = mapped_column(Numeric(6, 3), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    metrics: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
