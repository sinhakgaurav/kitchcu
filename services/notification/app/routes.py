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
from ckac_common.openapi import RESP_422

settings = get_settings()
redis_client: redis.Redis | None = None
event_publisher = EventPublisher(None)
http_client: httpx.AsyncClient | None = None

router = APIRouter()

TAG_WHATSAPP = "WhatsApp"
TAG_SUPPORT = "Support Chat"


def get_publisher() -> EventPublisher:
    return event_publisher


@router.get(
    "/webhooks/whatsapp",
    tags=[TAG_WHATSAPP],
    summary="Meta WhatsApp webhook verification handshake",
    description=(
        "**Auth:** None — Meta calls this once when configuring the webhook, matching "
        "`hub.verify_token` against `WHATSAPP_VERIFY_TOKEN`.\n\n"
        "**Query:** `hub.mode`, `hub.verify_token`, `hub.challenge` (Meta-defined names).\n\n"
        "**Response:** Echoes `hub.challenge` as an int on success; `403` on token mismatch, "
        "`503` if `WHATSAPP_VERIFY_TOKEN` is unconfigured outside dev/test."
    ),
    responses={403: {"description": "Verification token mismatch"}, 503: {"description": "Webhook not configured"}},
)
async def whatsapp_verify(
    session: Annotated[AsyncSession, Depends(get_db)],
    hub_mode: Annotated[str | None, Query(alias="hub.mode")] = None,
    hub_verify_token: Annotated[str | None, Query(alias="hub.verify_token")] = None,
    hub_challenge: Annotated[str | None, Query(alias="hub.challenge")] = None,
):
    from ckac_common.platform_config import get_platform_secret, is_non_production

    verify_token = await get_platform_secret(session, "whatsapp_verify_token")
    if not verify_token:
        verify_token = os.environ.get("WHATSAPP_VERIFY_TOKEN") or settings.whatsapp_verify_token
    if not is_non_production() and not verify_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WhatsApp verify token not configured",
        )
    if hub_mode == "subscribe" and hub_verify_token == verify_token:
        return int(hub_challenge or 0)
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verification failed")


@router.post(
    "/webhooks/whatsapp",
    tags=[TAG_WHATSAPP],
    summary="Receive inbound WhatsApp messages",
    description=(
        "**Auth:** None (Meta signs requests upstream; payload shape validation is the trust "
        "boundary here) — this is the live inbound message webhook Meta calls per conversation "
        "event.\n\n"
        "**Body:** Raw Meta Cloud API webhook payload (parsed internally, not a typed schema).\n\n"
        "**Behavior:** Parses each message, attempts to match it to a kitchen by the sending "
        "phone/context, and hands it to the draft-order parser (owner reviews/confirms drafts "
        "in the kitchen dashboard). `503` if the service has not finished startup.\n\n"
        "**Response:** `{processed, results}` — count and per-message outcome."
    ),
    responses={503: {"description": "Service not ready"}},
)
async def whatsapp_webhook(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
):
    from ckac_common.platform_config import (
        get_platform_secret,
        is_non_production,
        verify_meta_signature,
    )

    if not http_client:
        raise HTTPException(status_code=503, detail="Service not ready")

    raw = await request.body()
    app_secret = await get_platform_secret(session, "whatsapp_app_secret")
    if app_secret:
        signature = request.headers.get("X-Hub-Signature-256")
        if not verify_meta_signature(raw, signature, app_secret):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid WhatsApp webhook signature",
            )
    elif not is_non_production():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WhatsApp app secret not configured",
        )

    import json

    try:
        payload = json.loads(raw.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid webhook payload") from exc

    messages = parse_webhook(payload)
    results = []
    for msg in messages:
        result = await process_inbound_message(session, msg, publisher, http_client)
        results.append(result)
    return {"processed": len(results), "results": results}


@router.post(
    "/support/chat",
    response_model=SupportChatResponse,
    tags=[TAG_SUPPORT],
    summary="AI-assisted support chat (marketing site)",
    description=(
        "**Auth:** None — public, used by the owner/customer marketing-site chat widget.\n\n"
        "**Body:** `SupportChatRequest` — `audience`, `message`, and prior `history`.\n\n"
        "**Behavior:** Answers from a curated, accurate knowledge base by default (never "
        "hallucinated pricing/features); if `SUPPORT_AI_API_KEY` is configured, augments with an "
        "LLM using that knowledge as grounding. Detects escalation-worthy messages (complaints, "
        "explicit human requests) and flags `suggest_ticket` so the UI can offer **Raise ticket** "
        "(`POST /support/tickets`).\n\n"
        "**Response:** `SupportChatResponse`."
    ),
    responses={422: RESP_422},
)
async def support_chat(
    body: SupportChatRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SupportChatResponse:
    return await generate_support_reply(body, session=session)
