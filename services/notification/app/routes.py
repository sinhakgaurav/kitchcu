import os
from contextlib import asynccontextmanager
from typing import Annotated

import httpx
import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.handlers import process_inbound_message
from app.support import SupportChatRequest, SupportChatResponse, generate_support_reply
from app.whatsapp import extract_messages as parse_webhook
from ckac_common.config import get_settings
from ckac_common.database import get_db
from ckac_common.event_bus import EventPublisher

settings = get_settings()
redis_client: redis.Redis | None = None
event_publisher = EventPublisher(None)
http_client: httpx.AsyncClient | None = None

router = APIRouter()


def get_publisher() -> EventPublisher:
    return event_publisher


@router.get("/webhooks/whatsapp")
async def whatsapp_verify(
    hub_mode: Annotated[str | None, Query(alias="hub.mode")] = None,
    hub_verify_token: Annotated[str | None, Query(alias="hub.verify_token")] = None,
    hub_challenge: Annotated[str | None, Query(alias="hub.challenge")] = None,
):
    verify_token = os.environ.get("WHATSAPP_VERIFY_TOKEN") or settings.whatsapp_verify_token
    if settings.app_env not in ("development", "test") and not os.environ.get("WHATSAPP_VERIFY_TOKEN"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WHATSAPP_VERIFY_TOKEN not configured",
        )
    if hub_mode == "subscribe" and hub_verify_token == verify_token:
        return int(hub_challenge or 0)
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verification failed")


@router.post("/webhooks/whatsapp")
async def whatsapp_webhook(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
):
    if not http_client:
        raise HTTPException(status_code=503, detail="Service not ready")
    payload = await request.json()
    messages = parse_webhook(payload)
    results = []
    for msg in messages:
        result = await process_inbound_message(session, msg, publisher, http_client)
        results.append(result)
    return {"processed": len(results), "results": results}


@router.post("/support/chat", response_model=SupportChatResponse)
async def support_chat(body: SupportChatRequest) -> SupportChatResponse:
    """AI-assisted support for marketing site — owner & customer audiences."""
    return await generate_support_reply(body)
