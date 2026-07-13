import uuid

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.whatsapp import InboundMessage
from ckac_common.auth import stream_key
from ckac_common.config import get_settings
from ckac_common.event_bus import EventPublisher
from ckac_common.internal_auth import resolve_internal_api_key

settings = get_settings()


async def lookup_kitchen_id(session: AsyncSession, phone_number_id: str) -> uuid.UUID | None:
    result = await session.execute(
        text(
            "SELECT id FROM ckac_identity.kitchens "
            "WHERE whatsapp_phone_id = :pid AND status = 'active' LIMIT 1"
        ),
        {"pid": phone_number_id},
    )
    row = result.scalar_one_or_none()
    return row if row else None


async def process_inbound_message(
    session: AsyncSession,
    msg: InboundMessage,
    publisher: EventPublisher,
    http_client: httpx.AsyncClient,
) -> dict:
    kitchen_id = await lookup_kitchen_id(session, msg.phone_number_id)
    if not kitchen_id:
        return {"status": "ignored", "reason": "kitchen_not_found"}

    event = EventPublisher.build(
        event_type="whatsapp.message.received",
        aggregate_type="whatsapp_message",
        aggregate_id=msg.message_id or str(uuid.uuid4()),
        producer="notification-service",
        payload={
            "kitchen_id": str(kitchen_id),
            "from_phone": msg.from_phone,
            "text": msg.text,
            "phone_number_id": msg.phone_number_id,
        },
    )
    await publisher.publish(stream_key("notify", "whatsapp"), event, session=session)

    order_url = f"{settings.order_service_url}/api/v1/internal/kitchens/{kitchen_id}/orders/from-whatsapp"
    response = await http_client.post(
        order_url,
        json={"message_text": msg.text, "customer_phone": f"+{msg.from_phone.lstrip('+')}"},
        headers={"X-Internal-Key": resolve_internal_api_key()},
        timeout=30.0,
    )
    response.raise_for_status()
    draft = response.json()
    return {"status": "draft_created", "draft_id": draft["id"], "kitchen_id": str(kitchen_id)}
