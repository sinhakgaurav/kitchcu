"""Meta WhatsApp Cloud API outbound text messages."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import httpx

from ckac_common.platform_config import is_non_production

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.facebook.com/v19.0"


@dataclass(frozen=True)
class WhatsAppSendResult:
    ok: bool
    simulated: bool = False
    provider_message_id: str | None = None
    error: str | None = None


async def send_text_message(
    *,
    phone_number_id: str,
    to_phone: str,
    text: str,
    access_token: str,
) -> WhatsAppSendResult:
    """Send a WhatsApp Cloud API text message.

    In development/test without a real token, returns simulated success so CI
    and local demos stay green. Production without token/phone_id fails closed.
    """
    to = to_phone.strip().lstrip("+")
    if not phone_number_id or not access_token:
        if is_non_production():
            return WhatsAppSendResult(ok=True, simulated=True)
        return WhatsAppSendResult(ok=False, error="WhatsApp Cloud API not configured")

    # Explicit simulate flag for staging without Meta
    if os.environ.get("WHATSAPP_SIMULATE_SEND", "").strip().lower() in ("1", "true", "yes"):
        return WhatsAppSendResult(ok=True, simulated=True)

    url = f"{GRAPH_BASE}/{phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"preview_url": False, "body": text[:4096]},
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
            )
            if response.status_code >= 400:
                detail = response.text[:300]
                logger.warning("WhatsApp send failed %s: %s", response.status_code, detail)
                return WhatsAppSendResult(ok=False, error=f"meta_{response.status_code}")
            data = response.json()
            msg_id = None
            messages = data.get("messages") or []
            if messages:
                msg_id = messages[0].get("id")
            return WhatsAppSendResult(ok=True, provider_message_id=msg_id)
    except Exception as exc:
        logger.warning("WhatsApp send error: %s", exc)
        return WhatsAppSendResult(ok=False, error="transport_error")
