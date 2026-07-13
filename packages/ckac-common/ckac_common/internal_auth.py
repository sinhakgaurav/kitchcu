import os

from fastapi import Header, HTTPException, status

from ckac_common.config import get_settings


def resolve_internal_api_key() -> str:
    return os.environ.get("INTERNAL_API_KEY") or get_settings().internal_api_key


async def verify_internal_key(x_internal_key: str | None = Header(default=None)) -> None:
    if not x_internal_key or x_internal_key != resolve_internal_api_key():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid internal key")
