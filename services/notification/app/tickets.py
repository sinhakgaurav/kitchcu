"""Support ticket domain — create, list, update, reply."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, model_validator
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SupportTicket, SupportTicketMessage
from app.support import ChatMessage
from ckac_common.auth import stream_key
from ckac_common.event_bus import EventPublisher

Audience = Literal["owner", "customer"]
Category = Literal[
    "order_issue", "delivery", "quality", "billing", "technical", "complaint", "general"
]
Status = Literal["open", "in_progress", "waiting_customer", "resolved", "closed"]
Priority = Literal["low", "normal", "high", "urgent"]

ESCALATION_PATTERNS = [
    r"\b(complaint|complain|wrong order|missing item|refund|not delivered|late delivery)\b",
    r"\b(raise ticket|open ticket|create ticket|speak to human|talk to support|escalate)\b",
    r"\b(order issue|order problem|bad food|quality issue|never received)\b",
    r"\b(unhappy|disappointed|fraud|scam|report)\b",
]

CATEGORY_HINTS: list[tuple[str, Category]] = [
    (r"\b(refund|wrong order|missing|not received|order)\b", "order_issue"),
    (r"\b(late|delivery|driver|not delivered)\b", "delivery"),
    (r"\b(quality|taste|cold|stale|bad food)\b", "quality"),
    (r"\b(bill|payment|subscription|charge|billing)\b", "billing"),
    (r"\b(bug|error|login|technical|app)\b", "technical"),
    (r"\b(complaint|unhappy|report)\b", "complaint"),
]


def should_suggest_ticket(message: str, used_fallback: bool) -> bool:
    m = message.lower()
    if any(re.search(p, m) for p in ESCALATION_PATTERNS):
        return True
    return used_fallback and _match(m, r"\b(issue|problem|help|support)\b")


def infer_category(message: str, audience: Audience) -> Category:
    m = message.lower()
    for pattern, cat in CATEGORY_HINTS:
        if re.search(pattern, m):
            return cat
    if audience == "owner":
        return "technical"
    return "order_issue"


def _match(text: str, pattern: str) -> bool:
    return bool(re.search(pattern, text))


def default_priority(category: Category) -> Priority:
    if category in ("order_issue", "complaint", "delivery"):
        return "high"
    if category == "quality":
        return "normal"
    return "normal"


async def _next_ticket_number(session: AsyncSession) -> str:
    today = datetime.now(UTC).strftime("%Y%m%d")
    prefix = f"TKT-{today}-"
    result = await session.execute(
        select(func.count())
        .select_from(SupportTicket)
        .where(SupportTicket.ticket_number.like(f"{prefix}%"))
    )
    seq = int(result.scalar_one()) + 1
    return f"{prefix}{seq:04d}"


async def _resolve_order(session: AsyncSession, order_code: str | None) -> tuple[uuid.UUID | None, str | None, uuid.UUID | None]:
    if not order_code:
        return None, None, None
    code = order_code.strip().upper()
    row = (
        await session.execute(
            text(
                "SELECT id, order_code, kitchen_id FROM ckac_orders.orders "
                "WHERE UPPER(order_code) = :code LIMIT 1"
            ),
            {"code": code},
        )
    ).mappings().first()
    if not row:
        return None, code, None
    return row["id"], row["order_code"], row["kitchen_id"]


class TicketCreateRequest(BaseModel):
    audience: Audience
    category: Category
    subject: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=10, max_length=4000)
    customer_name: str | None = Field(None, max_length=255)
    customer_phone: str | None = Field(None, max_length=20)
    customer_email: EmailStr | None = None
    order_code: str | None = Field(None, max_length=64)
    kitchen_id: uuid.UUID | None = None
    source: Literal["ai_chat", "web_form"] = "ai_chat"
    chat_history: list[ChatMessage] = Field(default_factory=list, max_length=30)


class TicketMessageResponse(BaseModel):
    id: uuid.UUID
    author_type: str
    message: str
    created_at: datetime


class TicketResponse(BaseModel):
    id: uuid.UUID
    ticket_number: str
    audience: str
    category: str
    status: str
    priority: str
    subject: str
    description: str
    customer_name: str | None
    customer_phone: str | None
    customer_email: str | None
    order_id: uuid.UUID | None
    order_code: str | None
    kitchen_id: uuid.UUID | None
    source: str
    assigned_admin_id: uuid.UUID | None
    resolution_note: str | None
    created_at: datetime
    updated_at: datetime
    messages: list[TicketMessageResponse] = []


class TicketListResponse(BaseModel):
    tickets: list[TicketResponse]
    total: int


class TicketUpdateRequest(BaseModel):
    status: Status | None = None
    priority: Priority | None = None
    assigned_admin_id: uuid.UUID | None = None
    resolution_note: str | None = Field(None, max_length=2000)

    @model_validator(mode="after")
    def at_least_one_field(self) -> TicketUpdateRequest:
        if not any(
            v is not None
            for v in (self.status, self.priority, self.assigned_admin_id, self.resolution_note)
        ):
            raise ValueError("At least one field required")
        return self


class TicketReplyRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)


def _ticket_response(ticket: SupportTicket, messages: list[SupportTicketMessage] | None = None) -> TicketResponse:
    return TicketResponse(
        id=ticket.id,
        ticket_number=ticket.ticket_number,
        audience=ticket.audience,
        category=ticket.category,
        status=ticket.status,
        priority=ticket.priority,
        subject=ticket.subject,
        description=ticket.description,
        customer_name=ticket.customer_name,
        customer_phone=ticket.customer_phone,
        customer_email=ticket.customer_email,
        order_id=ticket.order_id,
        order_code=ticket.order_code,
        kitchen_id=ticket.kitchen_id,
        source=ticket.source,
        assigned_admin_id=ticket.assigned_admin_id,
        resolution_note=ticket.resolution_note,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        messages=[
            TicketMessageResponse(
                id=m.id, author_type=m.author_type, message=m.message, created_at=m.created_at
            )
            for m in (messages or [])
        ],
    )


async def create_ticket(
    session: AsyncSession,
    body: TicketCreateRequest,
    publisher: EventPublisher,
) -> TicketResponse:
    order_id, order_code, order_kitchen_id = await _resolve_order(session, body.order_code)
    kitchen_id = body.kitchen_id or order_kitchen_id
    priority = default_priority(body.category)
    now = datetime.now(UTC)
    ticket = SupportTicket(
        ticket_number=await _next_ticket_number(session),
        audience=body.audience,
        category=body.category,
        status="open",
        priority=priority,
        subject=body.subject.strip(),
        description=body.description.strip(),
        customer_name=body.customer_name,
        customer_phone=body.customer_phone,
        customer_email=str(body.customer_email) if body.customer_email else None,
        order_id=order_id,
        order_code=order_code,
        kitchen_id=kitchen_id,
        source=body.source,
        created_at=now,
        updated_at=now,
    )
    session.add(ticket)
    await session.flush()

    messages: list[SupportTicketMessage] = []
    initial = SupportTicketMessage(
        ticket_id=ticket.id,
        author_type="customer",
        message=body.description.strip(),
    )
    session.add(initial)
    messages.append(initial)

    for chat in body.chat_history[-10:]:
        author = "customer" if chat.role == "user" else "ai"
        msg = SupportTicketMessage(
            ticket_id=ticket.id,
            author_type=author,
            message=chat.content,
            meta={"from_chat": True},
        )
        session.add(msg)
        messages.append(msg)

    system_msg = SupportTicketMessage(
        ticket_id=ticket.id,
        author_type="system",
        message=f"Ticket created via {body.source}. Priority: {priority}.",
    )
    session.add(system_msg)
    messages.append(system_msg)

    event = EventPublisher.build(
        event_type="support.ticket.created",
        aggregate_type="support_ticket",
        aggregate_id=str(ticket.id),
        producer="notification-service",
        payload={
            "ticket_number": ticket.ticket_number,
            "audience": ticket.audience,
            "category": ticket.category,
            "priority": ticket.priority,
            "order_code": ticket.order_code,
        },
    )
    await publisher.publish(stream_key("notify", "support"), event, session=session)
    await session.flush()
    return _ticket_response(ticket, messages)


async def list_tickets(
    session: AsyncSession,
    *,
    status: str | None = None,
    audience: str | None = None,
    limit: int = 100,
) -> TicketListResponse:
    query = select(SupportTicket).order_by(SupportTicket.created_at.desc())
    if status:
        query = query.where(SupportTicket.status == status)
    if audience:
        query = query.where(SupportTicket.audience == audience)
    query = query.limit(min(limit, 500))
    tickets = list((await session.execute(query)).scalars().all())
    return TicketListResponse(
        tickets=[_ticket_response(t) for t in tickets],
        total=len(tickets),
    )


async def get_ticket(session: AsyncSession, ticket_id: uuid.UUID) -> TicketResponse:
    ticket = (
        await session.execute(select(SupportTicket).where(SupportTicket.id == ticket_id))
    ).scalar_one_or_none()
    if not ticket:
        raise ValueError("Ticket not found")
    msgs = list(
        (
            await session.execute(
                select(SupportTicketMessage)
                .where(SupportTicketMessage.ticket_id == ticket_id)
                .order_by(SupportTicketMessage.created_at)
            )
        ).scalars().all()
    )
    return _ticket_response(ticket, msgs)


async def update_ticket(
    session: AsyncSession,
    ticket_id: uuid.UUID,
    body: TicketUpdateRequest,
    admin_id: uuid.UUID,
    publisher: EventPublisher,
) -> TicketResponse:
    ticket = (
        await session.execute(select(SupportTicket).where(SupportTicket.id == ticket_id))
    ).scalar_one_or_none()
    if not ticket:
        raise ValueError("Ticket not found")

    if body.status is not None:
        ticket.status = body.status
    if body.priority is not None:
        ticket.priority = body.priority
    if body.assigned_admin_id is not None:
        ticket.assigned_admin_id = body.assigned_admin_id
    elif body.status == "in_progress" and not ticket.assigned_admin_id:
        ticket.assigned_admin_id = admin_id
    if body.resolution_note is not None:
        ticket.resolution_note = body.resolution_note
    ticket.updated_at = datetime.now(UTC)

    event = EventPublisher.build(
        event_type="support.ticket.updated",
        aggregate_type="support_ticket",
        aggregate_id=str(ticket.id),
        producer="notification-service",
        payload={"ticket_number": ticket.ticket_number, "status": ticket.status},
    )
    await publisher.publish(stream_key("notify", "support"), event, session=session)
    await session.flush()
    return await get_ticket(session, ticket_id)


async def reply_to_ticket(
    session: AsyncSession,
    ticket_id: uuid.UUID,
    body: TicketReplyRequest,
    admin_id: uuid.UUID,
    publisher: EventPublisher,
) -> TicketResponse:
    ticket = (
        await session.execute(select(SupportTicket).where(SupportTicket.id == ticket_id))
    ).scalar_one_or_none()
    if not ticket:
        raise ValueError("Ticket not found")

    session.add(
        SupportTicketMessage(
            ticket_id=ticket.id,
            author_type="admin",
            author_id=admin_id,
            message=body.message.strip(),
        )
    )
    if ticket.status == "open":
        ticket.status = "in_progress"
    if not ticket.assigned_admin_id:
        ticket.assigned_admin_id = admin_id
    ticket.updated_at = datetime.now(UTC)

    event = EventPublisher.build(
        event_type="support.ticket.replied",
        aggregate_type="support_ticket",
        aggregate_id=str(ticket.id),
        producer="notification-service",
        payload={"ticket_number": ticket.ticket_number},
    )
    await publisher.publish(stream_key("notify", "support"), event, session=session)
    await session.flush()
    return await get_ticket(session, ticket_id)
