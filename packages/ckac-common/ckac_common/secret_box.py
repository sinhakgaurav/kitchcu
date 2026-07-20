"""Encrypt platform / kitchen secrets at rest (Fernet keyed from JWT_SECRET)."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from ckac_common.config import get_settings


def _fernet() -> Fernet:
    digest = hashlib.sha256(get_settings().jwt_secret.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(plain: str | None) -> str | None:
    if plain is None or plain == "":
        return None
    return _fernet().encrypt(plain.encode("utf-8")).decode("ascii")


def decrypt_secret(token: str | None) -> str | None:
    if not token:
        return None
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):
        return None


def mask_secret(plain: str | None, *, keep: int = 4) -> str | None:
    if not plain:
        return None
    if keep <= 0:
        return "••••"
    if len(plain) <= keep:
        return "*" * len(plain)
    return ("*" * (len(plain) - keep)) + plain[-keep:]
