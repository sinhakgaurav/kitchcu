"""Shared input validators — phone, person name, email.

Every service that accepts a contact detail must apply the same rules, otherwise
a number rejected on owner registration slips in through a support ticket and
breaks WhatsApp delivery downstream. Identity re-exports these so its existing
``normalize_india_phone`` import sites keep working.
"""

from __future__ import annotations

import re
import unicodedata

__all__ = [
    "INDIA_DIAL",
    "INDIA_NATIONAL_LENGTH",
    "normalize_india_phone",
    "normalize_optional_india_phone",
    "normalize_person_name",
    "normalize_optional_person_name",
    "normalize_display_name",
    "normalize_email",
    "normalize_optional_email",
]

INDIA_DIAL = "91"
INDIA_NATIONAL_LENGTH = 10

_INDIA_MOBILE = re.compile(r"[6-9]\d{9}")


def normalize_india_phone(v: str) -> str:
    """Normalize an India mobile to E.164 ``+91XXXXXXXXXX``.

    Accepts the four shapes people actually send: bare ``9876543210``,
    ``+91``/``91`` prefixed, ``0091`` IDD, and a domestic trunk ``09876543210``.
    Rejects 11+ digit nationals and foreign country codes — the platform cannot
    deliver OTPs or order updates to them.
    """
    digits = re.sub(r"\D", "", v or "")
    # 0091… carries the same intent as +91….
    if digits.startswith("00"):
        digits = digits[2:]

    if len(digits) == INDIA_NATIONAL_LENGTH:
        national = digits
    elif len(digits) == len(INDIA_DIAL) + INDIA_NATIONAL_LENGTH and digits.startswith(INDIA_DIAL):
        national = digits[len(INDIA_DIAL) :]
    elif len(digits) == INDIA_NATIONAL_LENGTH + 1 and digits.startswith("0"):
        national = digits[1:]
    else:
        raise ValueError("Phone must be a 10-digit India mobile or +91XXXXXXXXXX")
    if not _INDIA_MOBILE.fullmatch(national):
        raise ValueError("Phone must be a valid 10-digit India mobile number starting 6-9")
    return f"+{INDIA_DIAL}{national}"


def normalize_optional_india_phone(v: str | None) -> str | None:
    """Same rules as :func:`normalize_india_phone`; blank/None passes through."""
    if v is None or not str(v).strip():
        return None
    return normalize_india_phone(str(v))


_NAME_PUNCTUATION = frozenset(" .-'\u2019")


def _is_name_char(ch: str) -> bool:
    """Letters, combining marks, and the punctuation real names contain.

    Marks (Unicode category ``M``) are essential: Indic scripts write vowels as
    combining matras, so ``\\w`` and ``\\p{L}`` alone reject perfectly ordinary
    Hindi, Marathi, Tamil, and Bengali names.
    """
    if ch in _NAME_PUNCTUATION:
        return True
    return unicodedata.category(ch)[0] in ("L", "M")


def normalize_person_name(v: str) -> str:
    """Display name: letters (any script), spaces, apostrophe/hyphen/dot."""
    cleaned = (v or "").strip()
    if len(cleaned) < 2:
        raise ValueError("Name must be at least 2 characters")
    if len(cleaned) > 120:
        raise ValueError("Name must be under 120 characters")
    if any(ch.isdigit() for ch in cleaned):
        raise ValueError("Name must not contain digits")
    if not all(_is_name_char(ch) for ch in cleaned):
        raise ValueError("Name may only contain letters, spaces, apostrophes, hyphens, or dots")
    if not any(unicodedata.category(ch)[0] == "L" for ch in cleaned):
        raise ValueError("Name must include at least one letter")
    return cleaned


def normalize_optional_person_name(v: str | None) -> str | None:
    if v is None or not str(v).strip():
        return None
    return normalize_person_name(str(v))


def normalize_display_name(v: str | None) -> str | None:
    """A label shown next to a record, not an identity a human typed.

    Deliberately looser than :func:`normalize_person_name`: digits are allowed,
    because identity assigns OTP signups a placeholder like ``Customer 0481``
    and that name travels onto every order they place. Strict person-name rules
    belong on registration and profile forms, where a person types their own
    name; here we only trim, cap the length, and strip control characters.
    """
    if v is None:
        return None
    cleaned = "".join(ch for ch in str(v) if ch.isprintable()).strip()
    if not cleaned:
        return None
    if len(cleaned) > 120:
        raise ValueError("Name must be under 120 characters")
    return cleaned


# Stricter than the HTML5 default: a dot-separated TLD is required so `a@b`
# cannot reach a mail provider that will only bounce it.
_EMAIL_OK = re.compile(r"^[^\s@]+@[^\s@]+\.[A-Za-z]{2,}$")


def normalize_email(v: str) -> str:
    cleaned = (v or "").strip().lower()
    if not cleaned:
        raise ValueError("Email is required")
    if len(cleaned) > 254:
        raise ValueError("Email must be under 254 characters")
    if not _EMAIL_OK.fullmatch(cleaned):
        raise ValueError("Enter a valid email address")
    return cleaned


def normalize_optional_email(v: str | None) -> str | None:
    if v is None or not str(v).strip():
        return None
    return normalize_email(str(v))
