import uuid
from datetime import datetime

from sqlalchemy import DateTime, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ckac_common.database import Base


class DeliveryQuote(Base):
    """Audit log of fee quotes (F27/F28/F31)."""

    __tablename__ = "delivery_quotes"
    __table_args__ = {"schema": "ckac_delivery"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    customer_lat: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    customer_lng: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    distance_km: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    fee: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    breakdown: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
