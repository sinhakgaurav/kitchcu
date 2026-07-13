import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin_auth import AdminContext, get_current_admin
from app.tickets import (
    TicketCreateRequest,
    TicketListResponse,
    TicketReplyRequest,
    TicketResponse,
    TicketUpdateRequest,
    create_ticket,
    get_ticket,
    list_tickets,
    reply_to_ticket,
    update_ticket,
)
from ckac_common.database import get_db
from ckac_common.event_bus import EventPublisher

public_router = APIRouter()
admin_router = APIRouter(prefix="/admin", tags=["admin-tickets"])


def get_publisher() -> EventPublisher:
    from app.main import event_publisher

    return event_publisher


@public_router.post("/support/tickets", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
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


@admin_router.get("/tickets", response_model=TicketListResponse)
async def admin_tickets_list(
    admin: Annotated[AdminContext, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    audience: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> TicketListResponse:
    _ = admin
    return await list_tickets(session, status=status_filter, audience=audience, limit=limit)


@admin_router.get("/tickets/{ticket_id}", response_model=TicketResponse)
async def admin_ticket_get(
    ticket_id: uuid.UUID,
    admin: Annotated[AdminContext, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TicketResponse:
    _ = admin
    try:
        return await get_ticket(session, ticket_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@admin_router.patch("/tickets/{ticket_id}", response_model=TicketResponse)
async def admin_ticket_update(
    ticket_id: uuid.UUID,
    body: TicketUpdateRequest,
    admin: Annotated[AdminContext, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> TicketResponse:
    try:
        ticket = await update_ticket(session, ticket_id, body, admin.id, publisher)
        await session.commit()
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ticket


@admin_router.post("/tickets/{ticket_id}/reply", response_model=TicketResponse)
async def admin_ticket_reply(
    ticket_id: uuid.UUID,
    body: TicketReplyRequest,
    admin: Annotated[AdminContext, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> TicketResponse:
    try:
        ticket = await reply_to_ticket(session, ticket_id, body, admin.id, publisher)
        await session.commit()
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ticket
