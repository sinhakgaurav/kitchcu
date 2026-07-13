"""Extract inbound WhatsApp Cloud API webhook payloads."""

from dataclasses import dataclass


@dataclass
class InboundMessage:
    phone_number_id: str
    from_phone: str
    text: str
    message_id: str | None = None


def extract_messages(payload: dict) -> list[InboundMessage]:
    messages: list[InboundMessage] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            metadata = value.get("metadata", {})
            phone_number_id = metadata.get("phone_number_id", "")
            for msg in value.get("messages", []):
                if msg.get("type") != "text":
                    continue
                body = msg.get("text", {}).get("body", "")
                if not body.strip():
                    continue
                messages.append(
                    InboundMessage(
                        phone_number_id=phone_number_id,
                        from_phone=msg.get("from", ""),
                        text=body.strip(),
                        message_id=msg.get("id"),
                    )
                )
    return messages
