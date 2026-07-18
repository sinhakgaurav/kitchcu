import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin_auth import AdminContext, get_current_admin
from app.customer_deps import get_current_customer_id, load_customer_contact
from app.tickets import (
    TicketCreateRequest,
    TicketListResponse,
    TicketReplyRequest,
    TicketResponse,
    TicketUpdateRequest,
    create_ticket,
    get_ticket,
    list_tickets,
    list_tickets_for_customer,
    reply_to_ticket,
    update_ticket,
)
from ckac_common.database import get_db
from ckac_common.event_bus import EventPublisher
from ckac_common.openapi import RESP_400, RESP_404, auth_errors

public_router = APIRouter()
admin_router = APIRouter(prefix='/admin')
customer_router = APIRouter()

TAG_TICKETS = "Support Tickets"
TAG_CUSTOMER = "Customer Support"


def get_publisher() -> EventPublisher:
    from app.main import event_publisher

    return event_publisher


@customer_router.get(
    "/customers/me/tickets",
    response_model=TicketListResponse,
    tags=[TAG_CUSTOMER],
    summary="List my complaints / tickets",
    responses=auth_errors(),
)
async def customer_tickets_list(
    customer_id: Annotated[uuid.UUID, Depends(get_current_customer_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TicketListResponse:
    from ckac_common.platform_config import require_feature

    try:
        await require_feature(session, "customer_complaints")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    contact = await load_customer_contact(customer_id, session)
    return await list_tickets_for_customer(
        session, customer_id, phone=contact.get("phone")
    )


@customer_router.post(
    "/customers/me/tickets",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
    tags=[TAG_CUSTOMER],
    summary="Raise a complaint / support ticket",
    responses={**auth_errors(), 400: RESP_400},
)
async def customer_tickets_create(
    body: TicketCreateRequest,
    customer_id: Annotated[uuid.UUID, Depends(get_current_customer_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> TicketResponse:
    from ckac_common.platform_config import require_feature

    try:
        await require_feature(session, "customer_complaints")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    contact = await load_customer_contact(customer_id, session)
    # Force customer audience + known contact
    payload = body.model_copy(
        update={
            "audience": "customer",
            "customer_name": body.customer_name or contact.get("name"),
            "customer_phone": body.customer_phone or contact.get("phone"),
            "customer_email": body.customer_email or contact.get("email"),
            "source": "web_form",
        }
    )
    return await create_ticket(session, payload, publisher, customer_id=customer_id)


@customer_router.get(
    "/customers/me/tickets/{ticket_id}",
    response_model=TicketResponse,
    tags=[TAG_CUSTOMER],
    summary="Get one of my tickets",
    responses={**auth_errors(), 404: RESP_404},
)
async def customer_tickets_get(
    ticket_id: uuid.UUID,
    customer_id: Annotated[uuid.UUID, Depends(get_current_customer_id)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TicketResponse:
    contact = await load_customer_contact(customer_id, session)
    try:
        ticket = await get_ticket(session, ticket_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    owns = ticket.customer_id == customer_id or (
        bool(contact.get("phone")) and ticket.customer_phone == contact.get("phone")
    )
    if not owns:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return ticket


@public_router.post(
    "/support/tickets",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
    tags=[TAG_TICKETS],
    summary="Create a support ticket",
    description=(
        "**Auth:** None — public. Called by the marketing-site 'Raise ticket' action or a "
        "standalone contact form.\n\n"
        "**Body:** `TicketCreateRequest` — audience, category, subject/description, optional "
        "reporter contact info, optional `order_code` (auto-resolved to `order_id`/`kitchen_id`), "
        "and prior chat history for context.\n\n"
        "**Behavior:** Assigns a ticket number (`TKT-YYYYMMDD-NNNN`), seeds the message timeline "
        "with the description + chat history, sets `status='open'` with a category-based default "
        "priority, and publishes `support.ticket.created`.\n\n"
        "**Response:** Created `TicketResponse` with the full initial timeline."
    ),
    responses={400: RESP_400},
)
async def ticket_create(
    body: TicketCreateRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> TicketResponse:
    try:
        ticket = await create_ticket(session, body, publisher)
        await session.commit()
    except Exception as exc:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ticket


@admin_router.get(
    "/tickets",
    response_model=TicketListResponse,
    tags=[TAG_TICKETS],
    summary="List support tickets (platform admin)",
    description=(
        "**Auth:** Platform admin JWT (`type: admin`).\n\n"
        "**Query:** `status`, `audience` filters; `limit` (1-500, default 100).\n\n"
        "**Response:** `TicketListResponse` ordered newest first (message timelines omitted for brevity)."
    ),
    responses=auth_errors(),
)
async def admin_tickets_list(
    admin: Annotated[AdminContext, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
    status_filter: Annotated[str | None, Query(alias="status", description="Filter by ticket status.")] = None,
    audience: Annotated[str | None, Query(description="Filter by 'owner' or 'customer'.")] = None,
    limit: Annotated[int, Query(ge=1, le=500, description="Max tickets to return (1-500).")] = 100,
) -> TicketListResponse:
    from ckac_common.admin_rbac import assert_admin_permission

    await assert_admin_permission(session, role=admin.role, permission="tickets:write")
    return await list_tickets(session, status=status_filter, audience=audience, limit=limit)


@admin_router.get(
    "/tickets/{ticket_id}",
    response_model=TicketResponse,
    tags=[TAG_TICKETS],
    summary="Get a ticket with its full message timeline",
    description=(
        "**Auth:** Platform admin JWT.\n\n"
        "**Response:** `TicketResponse` including every message (customer/AI/system/admin), "
        "oldest first. 404 if the ticket does not exist."
    ),
    responses={**auth_errors(), 404: RESP_404},
)
async def admin_ticket_get(
    ticket_id: uuid.UUID,
    admin: Annotated[AdminContext, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TicketResponse:
    from ckac_common.admin_rbac import assert_admin_permission

    await assert_admin_permission(session, role=admin.role, permission="tickets:write")
    try:
        return await get_ticket(session, ticket_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@admin_router.patch(
    "/tickets/{ticket_id}",
    response_model=TicketResponse,
    tags=[TAG_TICKETS],
    summary="Update a ticket's status/priority/assignment",
    description=(
        "**Auth:** Platform admin JWT.\n\n"
        "**Body:** `TicketUpdateRequest` — at least one of `status`, `priority`, "
        "`assigned_admin_id`, `resolution_note`. Moving `status` to `in_progress` without an "
        "explicit assignee auto-assigns the caller.\n\n"
        "**Response:** Updated `TicketResponse` with full timeline. Publishes "
        "`support.ticket.updated`. 404 if the ticket does not exist."
    ),
    responses={**auth_errors(), 404: RESP_404, 422: {"description": "No update field provided"}},
)
async def admin_ticket_update(
    ticket_id: uuid.UUID,
    body: TicketUpdateRequest,
    admin: Annotated[AdminContext, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> TicketResponse:
    from ckac_common.admin_rbac import assert_admin_permission

    await assert_admin_permission(session, role=admin.role, permission="tickets:write")
    try:
        ticket = await update_ticket(session, ticket_id, body, admin.id, publisher)
        await session.commit()
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ticket


@admin_router.post(
    "/tickets/{ticket_id}/reply",
    response_model=TicketResponse,
    tags=[TAG_TICKETS],
    summary="Reply to a ticket",
    description=(
        "**Auth:** Platform admin JWT.\n\n"
        "**Body:** `TicketReplyRequest` — reply text, appended as an `admin`-authored message.\n\n"
        "**Behavior:** Auto-moves `status` from `open` to `in_progress` and assigns the caller "
        "if unassigned. Publishes `support.ticket.replied`.\n\n"
        "**Response:** Updated `TicketResponse` with full timeline. 404 if the ticket does not exist."
    ),
    responses={**auth_errors(), 404: RESP_404},
)
async def admin_ticket_reply(
    ticket_id: uuid.UUID,
    body: TicketReplyRequest,
    admin: Annotated[AdminContext, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> TicketResponse:
    from ckac_common.admin_rbac import assert_admin_permission

    await assert_admin_permission(session, role=admin.role, permission="tickets:write")
    try:
        ticket = await reply_to_ticket(session, ticket_id, body, admin.id, publisher)
        await session.commit()
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ticket
