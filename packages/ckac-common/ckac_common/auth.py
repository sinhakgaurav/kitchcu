import uuid

from jose import JWTError, jwt
from fastapi import HTTPException, status

from ckac_common.config import get_settings
from ckac_common.events import EventEnvelope

settings = get_settings()


def decode_customer_id(token: str) -> uuid.UUID:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != "customer":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        return uuid.UUID(payload["sub"])
    except (JWTError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc


def decode_owner_id(token: str) -> uuid.UUID:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != "owner":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        return uuid.UUID(payload["sub"])
    except (JWTError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc


def stream_key(domain: str, aggregate: str) -> str:
    """Redis stream key: ckac:catalog:dish"""
    return f"ckac:{domain}:{aggregate}"


def event_to_stream_fields(event: EventEnvelope) -> dict[str, str]:
    return {"data": event.model_dump_json()}
