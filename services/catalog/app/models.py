import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from ckac_common.database import Base

DEFAULT_CATEGORY_SLUGS = [
    ("Veg", "veg"),
    ("Non Veg", "non_veg"),
    ("Vegan", "vegan"),
    ("Eggetarian", "eggetarian"),
    ("Beverages", "beverages"),
    ("Hot Drinks", "hot_drinks"),
    ("Cold Drinks", "cold_drinks"),
    ("Snacks", "snacks"),
    ("Desserts", "desserts"),
    ("Combos", "combos"),
    ("Seasonal Special", "seasonal_special"),
]

DEFAULT_CUISINES = [
    ("North Indian", "north_indian"),
    ("South Indian", "south_indian"),
    ("Maharashtrian", "maharashtrian"),
    ("Chinese", "chinese"),
    ("Continental", "continental"),
    ("Street Food", "street_food"),
    ("Home Style", "home_style"),
    ("Bengali", "bengali"),
]


class Cuisine(Base):
    __tablename__ = "cuisines"
    __table_args__ = {"schema": "ckac_catalog"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(50), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = {"schema": "ckac_catalog"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(50), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Dish(Base):
    __tablename__ = "dishes"
    __table_args__ = {"schema": "ckac_catalog"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    cuisine_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ckac_catalog.cuisines.id"), nullable=True
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ckac_catalog.categories.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    prep_time_min: Mapped[int] = mapped_column(Integer, default=30)
    delivery_time_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_time_min: Mapped[int] = mapped_column(Integer, default=30)
    ingredients_description: Mapped[str | None] = mapped_column(Text)
    quality_measures: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    is_chefs_special: Mapped[bool] = mapped_column(Boolean, default=False)
    is_unique_recipe: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class DishMedia(Base):
    __tablename__ = "dish_media"
    __table_args__ = {"schema": "ckac_catalog"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dish_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ckac_catalog.dishes.id"), nullable=False
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    is_hero: Mapped[bool] = mapped_column(Boolean, default=False)
    is_live_capture: Mapped[bool] = mapped_column(Boolean, default=False)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Ingredient(Base):
    __tablename__ = "ingredients"
    __table_args__ = {"schema": "ckac_catalog"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    current_stock: Mapped[float] = mapped_column(Numeric(12, 3), default=0)
    low_stock_threshold: Mapped[float] = mapped_column(Numeric(12, 3), default=0)
    photo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class DishIngredient(Base):
    __tablename__ = "dish_ingredients"
    __table_args__ = {"schema": "ckac_catalog"}

    dish_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ckac_catalog.dishes.id", ondelete="CASCADE"), primary_key=True
    )
    ingredient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ckac_catalog.ingredients.id", ondelete="CASCADE"),
        primary_key=True,
    )
    quantity: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    photo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class DishPrepStep(Base):
    __tablename__ = "dish_prep_steps"
    __table_args__ = {"schema": "ckac_catalog"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dish_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ckac_catalog.dishes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    body_html: Mapped[str] = mapped_column(Text, nullable=False)
    photo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class KitchenStockSettings(Base):
    """F19b — when pantry deducts: per-order ready vs bulk prep only."""

    __tablename__ = "kitchen_stock_settings"
    __table_args__ = {"schema": "ckac_catalog"}

    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    deduct_mode: Mapped[str] = mapped_column(String(32), default="order_ready", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class PrepBatch(Base):
    __tablename__ = "prep_batches"
    __table_args__ = {"schema": "ckac_catalog"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    batch_type: Mapped[str] = mapped_column(String(32), nullable=False)
    portions: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    prepared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class PrepBatchDish(Base):
    __tablename__ = "prep_batch_dishes"
    __table_args__ = {"schema": "ckac_catalog"}

    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ckac_catalog.prep_batches.id", ondelete="CASCADE"),
        primary_key=True,
    )
    dish_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ckac_catalog.dishes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    quantity_per_portion: Mapped[float] = mapped_column(Numeric(12, 3), default=1)


class PrepBatchIngredient(Base):
    __tablename__ = "prep_batch_ingredients"
    __table_args__ = {"schema": "ckac_catalog"}

    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ckac_catalog.prep_batches.id", ondelete="CASCADE"),
        primary_key=True,
    )
    ingredient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ckac_catalog.ingredients.id", ondelete="CASCADE"),
        primary_key=True,
    )
    quantity: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
