"""Kitchen WhatsApp / email marketing template CRUD."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Boolean, DateTime, String, Text, select
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from ckac_common.auth import stream_key
from ckac_common.database import Base
from ckac_common.event_bus import EventPublisher

CHANNELS = ("whatsapp", "email")
_VAR_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


class MessageTemplate(Base):
    __tablename__ = "message_templates"
    __table_args__ = {"schema": "ckac_marketing"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kitchen_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[list] = mapped_column(JSONB, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TemplateResponse(BaseModel):
    id: uuid.UUID
    kitchen_id: uuid.UUID
    channel: str
    name: str
    subject: str | None
    body: str
    variables: list[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None


class TemplateCreateRequest(BaseModel):
    channel: str = Field(..., description="whatsapp | email")
    name: str = Field(..., min_length=2, max_length=120)
    subject: str | None = Field(default=None, max_length=255)
    body: str = Field(..., min_length=5, max_length=8000)
    is_active: bool = True

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, v: str) -> str:
        c = v.strip().lower()
        if c not in CHANNELS:
            raise ValueError("channel must be whatsapp or email")
        return c


class TemplateUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    subject: str | None = Field(default=None, max_length=255)
    body: str | None = Field(default=None, min_length=5, max_length=8000)
    is_active: bool | None = None


def _extract_variables(body: str, subject: str | None) -> list[str]:
    found = set(_VAR_RE.findall(body or ""))
    if subject:
        found.update(_VAR_RE.findall(subject))
    return sorted(found)


def _to_response(row: MessageTemplate) -> TemplateResponse:
    return TemplateResponse(
        id=row.id,
        kitchen_id=row.kitchen_id,
        channel=row.channel,
        name=row.name,
        subject=row.subject,
        body=row.body,
        variables=list(row.variables or []),
        is_active=bool(row.is_active),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def list_templates(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    channel: str | None = None,
) -> list[TemplateResponse]:
    q = select(MessageTemplate).where(MessageTemplate.kitchen_id == kitchen_id)
    if channel:
        q = q.where(MessageTemplate.channel == channel)
    q = q.order_by(MessageTemplate.updated_at.desc().nullslast(), MessageTemplate.created_at.desc())
    rows = list((await session.execute(q)).scalars().all())
    return [_to_response(r) for r in rows]


async def create_template(
    session: AsyncSession,
    publisher: EventPublisher,
    kitchen_id: uuid.UUID,
    body: TemplateCreateRequest,
) -> TemplateResponse:
    if body.channel == "email" and not (body.subject and body.subject.strip()):
        raise HTTPException(status_code=400, detail="Email templates require a subject")
    row = MessageTemplate(
        kitchen_id=kitchen_id,
        channel=body.channel,
        name=body.name.strip(),
        subject=body.subject.strip() if body.subject else None,
        body=body.body.strip(),
        variables=_extract_variables(body.body, body.subject),
        is_active=body.is_active,
    )
    session.add(row)
    await session.flush()
    event = EventPublisher.build(
        event_type="message_template.created",
        aggregate_type="message_template",
        aggregate_id=str(row.id),
        producer="marketing-service",
        payload={
            "kitchen_id": str(kitchen_id),
            "channel": row.channel,
            "name": row.name,
        },
    )
    await publisher.publish(stream_key("marketing", "template"), event, session=session)
    return _to_response(row)


async def update_template(
    session: AsyncSession,
    publisher: EventPublisher,
    kitchen_id: uuid.UUID,
    template_id: uuid.UUID,
    body: TemplateUpdateRequest,
) -> TemplateResponse:
    row = (
        await session.execute(
            select(MessageTemplate).where(
                MessageTemplate.id == template_id,
                MessageTemplate.kitchen_id == kitchen_id,
            )
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Template not found")
    if body.name is not None:
        row.name = body.name.strip()
    if body.subject is not None:
        row.subject = body.subject.strip() or None
    if body.body is not None:
        row.body = body.body.strip()
    if body.is_active is not None:
        row.is_active = body.is_active
    if row.channel == "email" and not row.subject:
        raise HTTPException(status_code=400, detail="Email templates require a subject")
    row.variables = _extract_variables(row.body, row.subject)
    row.updated_at = datetime.now(UTC)
    await session.flush()
    event = EventPublisher.build(
        event_type="message_template.updated",
        aggregate_type="message_template",
        aggregate_id=str(row.id),
        producer="marketing-service",
        payload={"kitchen_id": str(kitchen_id), "channel": row.channel},
    )
    await publisher.publish(stream_key("marketing", "template"), event, session=session)
    return _to_response(row)


async def delete_template(
    session: AsyncSession,
    publisher: EventPublisher,
    kitchen_id: uuid.UUID,
    template_id: uuid.UUID,
) -> None:
    row = (
        await session.execute(
            select(MessageTemplate).where(
                MessageTemplate.id == template_id,
                MessageTemplate.kitchen_id == kitchen_id,
            )
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Template not found")
    await session.delete(row)
    await session.flush()
    event = EventPublisher.build(
        event_type="message_template.deleted",
        aggregate_type="message_template",
        aggregate_id=str(template_id),
        producer="marketing-service",
        payload={"kitchen_id": str(kitchen_id)},
    )
    await publisher.publish(stream_key("marketing", "template"), event, session=session)


class TemplateSendRequest(BaseModel):
    audience: str = Field(default="all", description="all | vip | repeat | churn_risk | phones")
    phones: list[str] = Field(default_factory=list, max_length=50)
    dry_run: bool = False
    sample_vars: dict[str, str] = Field(default_factory=dict)


class TemplateSendResponse(BaseModel):
    template_id: uuid.UUID
    channel: str
    queued: int
    dry_run: bool
    preview: str
    recipient_phones: list[str]


def _render_template(body: str, variables: dict[str, str]) -> str:
    out = body
    for key, val in variables.items():
        out = out.replace("{{ " + key + " }}", val)
        out = out.replace("{{" + key + "}}", val)
    return out


async def _resolve_audience_phones(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    audience: str,
    phones: list[str],
) -> list[str]:
    aud = audience.strip().lower()
    if aud == "phones":
        cleaned: list[str] = []
        for p in phones:
            p = p.strip()
            if p and p not in cleaned:
                cleaned.append(p)
        return cleaned[:50]

    from app.models import KitchenCustomer

    customers = list(
        (
            await session.execute(select(KitchenCustomer).where(KitchenCustomer.kitchen_id == kitchen_id))
        )
        .scalars()
        .all()
    )
    result: list[str] = []
    for cust in customers:
        phone = str(cust.customer_phone)
        tags = [str(t).lower() for t in (cust.tags or [])]
        if aud == "all":
            result.append(phone)
        elif aud in tags or aud.replace("_", "-") in tags:
            result.append(phone)
        elif aud == "vip" and float(cust.total_spend or 0) >= 2000:
            result.append(phone)
        elif aud == "repeat" and int(cust.order_count or 0) >= 2:
            result.append(phone)
        elif aud == "churn_risk" and "churn" in " ".join(tags):
            result.append(phone)
    seen: set[str] = set()
    out: list[str] = []
    for p in result:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out[:200]


async def send_template(
    session: AsyncSession,
    publisher: EventPublisher,
    kitchen_id: uuid.UUID,
    template_id: uuid.UUID,
    body: TemplateSendRequest,
) -> TemplateSendResponse:
    row = (
        await session.execute(
            select(MessageTemplate).where(
                MessageTemplate.id == template_id,
                MessageTemplate.kitchen_id == kitchen_id,
            )
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Template not found")
    if not row.is_active:
        raise HTTPException(status_code=400, detail="Template is inactive")

    recipients = await _resolve_audience_phones(
        session, kitchen_id, body.audience, body.phones
    )
    if not recipients and not body.dry_run:
        raise HTTPException(status_code=400, detail="No recipients matched this audience")

    defaults = {
        "customer_name": "Guest",
        "dish_name": "today's special",
        "kitchen_name": "our kitchen",
        "order_code": "",
        "menu_line": "chef specials",
        "storefront_url": "",
        "tagline": "",
    }
    defaults.update({k: str(v) for k, v in body.sample_vars.items()})
    preview = _render_template(row.body, defaults)
    if row.channel == "email" and row.subject:
        preview = f"Subject: {_render_template(row.subject, defaults)}\n\n{preview}"

    event = EventPublisher.build(
        event_type="message_template.send_requested",
        aggregate_type="message_template",
        aggregate_id=str(row.id),
        producer="marketing-service",
        payload={
            "kitchen_id": str(kitchen_id),
            "channel": row.channel,
            "audience": body.audience,
            "queued": len(recipients),
            "dry_run": body.dry_run,
            "preview": preview[:500],
        },
    )
    await publisher.publish(stream_key("marketing", "template"), event, session=session)

    if not body.dry_run and row.channel == "whatsapp" and recipients:
        from ckac_common.risk_config import is_risk_capability_enabled, messaging_fee_per_recipient_inr

        if await is_risk_capability_enabled(session, "messaging_wallet_deduct", default=True):
            fee = round(len(recipients) * messaging_fee_per_recipient_inr(), 2)
            if fee > 0:
                from app.billing_client import deduct_messaging_wallet

                ok = await deduct_messaging_wallet(
                    kitchen_id,
                    amount_inr=fee,
                    reason="marketing_template_blast",
                    recipient_count=len(recipients),
                )
                if not ok:
                    raise HTTPException(
                        status_code=status.HTTP_402_PAYMENT_REQUIRED,
                        detail="Insufficient messaging wallet balance for broadcast",
                    )

        from app.notify_client import notify_template_blast

        await notify_template_blast(
            kitchen_id=kitchen_id,
            message=preview,
            recipient_phones=recipients,
            template_name=row.name,
        )

    return TemplateSendResponse(
        template_id=row.id,
        channel=row.channel,
        queued=len(recipients),
        dry_run=body.dry_run,
        preview=preview,
        recipient_phones=recipients[:20],
    )
