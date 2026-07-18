"""Append-only platform admin audit log."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, String, func, select
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from ckac_common.database import Base
from ckac_common.observability import get_correlation_id


class AdminAuditEvent(Base):
    __tablename__ = "admin_audit_events"
    __table_args__ = {"schema": "ckac_identity"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_admin_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_email: Mapped[str] = mapped_column(String(255), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(32), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(64), nullable=False)
    kitchen_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    summary: Mapped[str] = mapped_column(String(500), default="")
    before: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    after: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class AdminAuditEventRow(BaseModel):
    id: uuid.UUID
    actor_admin_id: uuid.UUID | None
    actor_email: str
    actor_role: str
    action: str
    resource_type: str
    resource_id: str
    kitchen_id: uuid.UUID | None = None
    summary: str
    before: dict | None = None
    after: dict | None = None
    correlation_id: str | None = None
    created_at: datetime


class AdminAuditListResponse(BaseModel):
    total: int
    items: list[AdminAuditEventRow] = Field(default_factory=list)


async def record_admin_audit(
    session: AsyncSession,
    *,
    actor=None,
    action: str,
    resource_type: str,
    resource_id: str,
    kitchen_id: uuid.UUID | None = None,
    summary: str = "",
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    actor_admin_id: uuid.UUID | None = None,
    actor_email: str | None = None,
    actor_role: str | None = None,
) -> AdminAuditEvent:
    row = AdminAuditEvent(
        actor_admin_id=actor_admin_id if actor_admin_id is not None else getattr(actor, "id", None),
        actor_email=str(
            actor_email if actor_email is not None else getattr(actor, "email", "") or ""
        ),
        actor_role=str(
            actor_role if actor_role is not None else getattr(actor, "role", "") or ""
        ),
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id),
        kitchen_id=kitchen_id,
        summary=(summary or "")[:500],
        before=before,
        after=after,
        correlation_id=get_correlation_id(),
    )
    session.add(row)
    await session.flush()
    return row


async def list_admin_audit_events(
    session: AsyncSession,
    *,
    limit: int = 50,
    offset: int = 0,
    actor_email: str | None = None,
    resource_type: str | None = None,
    kitchen_id: uuid.UUID | None = None,
) -> AdminAuditListResponse:
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    stmt = select(AdminAuditEvent).order_by(AdminAuditEvent.created_at.desc())
    if actor_email:
        stmt = stmt.where(AdminAuditEvent.actor_email == actor_email.lower().strip())
    if resource_type:
        stmt = stmt.where(AdminAuditEvent.resource_type == resource_type)
    if kitchen_id:
        stmt = stmt.where(AdminAuditEvent.kitchen_id == kitchen_id)

    count_stmt = select(func.count()).select_from(AdminAuditEvent)
    if actor_email:
        count_stmt = count_stmt.where(AdminAuditEvent.actor_email == actor_email.lower().strip())
    if resource_type:
        count_stmt = count_stmt.where(AdminAuditEvent.resource_type == resource_type)
    if kitchen_id:
        count_stmt = count_stmt.where(AdminAuditEvent.kitchen_id == kitchen_id)
    total = int((await session.execute(count_stmt)).scalar_one() or 0)
    rows = list((await session.execute(stmt.offset(offset).limit(limit))).scalars().all())

    return AdminAuditListResponse(
        total=total,
        items=[
            AdminAuditEventRow(
                id=r.id,
                actor_admin_id=r.actor_admin_id,
                actor_email=r.actor_email,
                actor_role=r.actor_role,
                action=r.action,
                resource_type=r.resource_type,
                resource_id=r.resource_id,
                kitchen_id=r.kitchen_id,
                summary=r.summary,
                before=r.before,
                after=r.after,
                correlation_id=r.correlation_id,
                created_at=r.created_at,
            )
            for r in rows
        ],
    )
