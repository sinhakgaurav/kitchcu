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
    """Create a support ticket — from the AI chat widget ('Raise ticket') or a standalone web form."""

    audience: Audience = Field(..., description="'owner' or 'customer' — routes triage to the right team context.")
    category: Category = Field(..., description="Ticket category: order_issue, delivery, quality, billing, technical, complaint, or general.")
    subject: str = Field(..., min_length=3, max_length=255, description="Short ticket subject line.", examples=["Order not delivered"])
    description: str = Field(..., min_length=10, max_length=4000, description="Full description of the issue.")
    customer_name: str | None = Field(None, max_length=255, description="Reporter's name, if provided.")
    customer_phone: str | None = Field(None, max_length=20, description="Reporter's phone, if provided (never logged elsewhere as PII).")
    customer_email: EmailStr | None = Field(default=None, description="Reporter's email, if provided.")
    order_code: str | None = Field(None, max_length=64, description="Related order code, if this is order-related; resolved server-side to `order_id`/`kitchen_id`.", examples=["CKPNQ001-BILL-20260712-0042"])
    kitchen_id: uuid.UUID | None = Field(default=None, description="Related kitchen UUID; auto-filled from `order_code` if omitted and the order resolves.")
    source: Literal["ai_chat", "web_form"] = Field(default="ai_chat", description="Where the ticket originated.")
    chat_history: list[ChatMessage] = Field(default_factory=list, max_length=30, description="Prior AI-chat turns for context (last 10 attached to the ticket timeline).")


class TicketMessageResponse(BaseModel):
    """One message in a ticket's timeline (customer, AI, system, or admin authored)."""

    id: uuid.UUID = Field(..., description="Message UUID.")
    author_type: str = Field(..., description="'customer', 'ai', 'system', or 'admin'.")
    message: str = Field(..., description="Message text.")
    created_at: datetime = Field(..., description="Timestamp, UTC.")


class TicketResponse(BaseModel):
    """A support ticket with its full message timeline."""

    id: uuid.UUID = Field(..., description="Ticket UUID.")
    ticket_number: str = Field(..., description="Human-facing ticket number.", examples=["TKT-20260712-0007"])
    audience: str = Field(..., description="'owner' or 'customer'.")
    category: str = Field(..., description="Ticket category.")
    status: str = Field(..., description="'open', 'in_progress', 'waiting_customer', 'resolved', or 'closed'.")
    priority: str = Field(..., description="'low', 'normal', 'high', or 'urgent' — defaulted by category, adjustable by admin.")
    subject: str = Field(..., description="Ticket subject line.")
    description: str = Field(..., description="Original issue description.")
    customer_name: str | None = Field(default=None, description="Reporter's name, if provided.")
    customer_phone: str | None = Field(default=None, description="Reporter's phone, if provided.")
    customer_email: str | None = Field(default=None, description="Reporter's email, if provided.")
    customer_id: uuid.UUID | None = Field(default=None, description="Linked customer account, if signed in.")
    order_id: uuid.UUID | None = Field(default=None, description="Resolved order UUID, if `order_code` matched an order.")
    order_code: str | None = Field(default=None, description="Order code as provided/resolved.")
    kitchen_id: uuid.UUID | None = Field(default=None, description="Related kitchen UUID, if known.")
    source: str = Field(..., description="'ai_chat' or 'web_form'.")
    assigned_admin_id: uuid.UUID | None = Field(default=None, description="Platform admin currently assigned, if any.")
    resolution_note: str | None = Field(default=None, description="Admin's resolution note, once resolved.")
    created_at: datetime = Field(..., description="Creation timestamp, UTC.")
    updated_at: datetime = Field(..., description="Last update timestamp, UTC.")
    messages: list[TicketMessageResponse] = Field(default=[], description="Full timeline (included on create/get; omitted on list views).")


class TicketListResponse(BaseModel):
    """Admin ticket roster (list view — timelines omitted for brevity)."""

    tickets: list[TicketResponse] = Field(..., description="Tickets ordered newest first.")
    total: int = Field(..., description="Number of tickets returned (capped at 500 per request).")


class TicketUpdateRequest(BaseModel):
    """Platform admin partial update to a ticket — at least one field required."""

    status: Status | None = Field(default=None, description="New status.")
    priority: Priority | None = Field(default=None, description="New priority.")
    assigned_admin_id: uuid.UUID | None = Field(
        default=None,
        description=(
            "Reassign to a different admin, or null to unassign. "
            "Auto-assigned to the caller when status moves to 'in_progress' without an explicit value."
        ),
    )
    resolution_note: str | None = Field(None, max_length=2000, description="Resolution note, typically set alongside `status='resolved'`.")

    @model_validator(mode="after")
    def at_least_one_field(self) -> TicketUpdateRequest:
        # Allow explicit null for assigned_admin_id (unassign) via model_fields_set
        if not self.model_fields_set:
            raise ValueError("At least one field required")
        return self


class TicketReplyRequest(BaseModel):
    """Platform admin reply appended to a ticket's timeline."""

    message: str = Field(..., min_length=1, max_length=4000, description="Admin's reply text.")


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
        customer_id=ticket.customer_id,
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
    *,
    customer_id: uuid.UUID | None = None,
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
        customer_id=customer_id,
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


async def list_tickets_for_customer(
    session: AsyncSession,
    customer_id: uuid.UUID,
    *,
    phone: str | None = None,
    limit: int = 100,
) -> TicketListResponse:
    from sqlalchemy import or_

    if phone:
        query = (
            select(SupportTicket)
            .where(
                or_(
                    SupportTicket.customer_id == customer_id,
                    SupportTicket.customer_phone == phone,
                )
            )
            .order_by(SupportTicket.created_at.desc())
            .limit(limit)
        )
    else:
        query = (
            select(SupportTicket)
            .where(SupportTicket.customer_id == customer_id)
            .order_by(SupportTicket.created_at.desc())
            .limit(limit)
        )
    result = await session.execute(query)
    tickets = list(result.scalars().all())
    return TicketListResponse(
        tickets=[_ticket_response(t) for t in tickets],
        total=len(tickets),
    )


async def list_tickets(
    session: AsyncSession,
    *,
    status: str | None = None,
    audience: str | None = None,
    kitchen_id: uuid.UUID | None = None,
    customer_id: uuid.UUID | None = None,
    limit: int = 100,
) -> TicketListResponse:
    query = select(SupportTicket).order_by(SupportTicket.created_at.desc())
    if status:
        query = query.where(SupportTicket.status == status)
    if audience:
        query = query.where(SupportTicket.audience == audience)
    if kitchen_id is not None:
        query = query.where(SupportTicket.kitchen_id == kitchen_id)
    if customer_id is not None:
        query = query.where(SupportTicket.customer_id == customer_id)
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
    if "assigned_admin_id" in body.model_fields_set:
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
