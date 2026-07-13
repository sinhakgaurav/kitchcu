"""Customer authentication — OAuth, WhatsApp OTP, JWT."""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime, timedelta

from jose import jwt
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Customer, CustomerOAuthIdentity
from app.oauth import OAuthProfile, SUPPORTED_OAUTH_PROVIDERS
from ckac_common.config import get_settings

settings = get_settings()

_CUSTOMER_OTP: dict[str, str] = {}


class CustomerResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str | None
    phone: str | None
    avatar_url: str | None
    status: str

    model_config = {"from_attributes": True}


class CustomerAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    customer: CustomerResponse


class OAuthStartResponse(BaseModel):
    provider: str
    state: str
    authorization_url: str | None = None
    dev_mode: bool = False


class OAuthCompleteRequest(BaseModel):
    code: str
    state: str
    redirect_uri: str


class CustomerPhoneRequest(BaseModel):
    phone: str = Field(..., min_length=10, max_length=15)

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, v: str) -> str:
        digits = re.sub(r"\D", "", v)
        if len(digits) < 10:
            raise ValueError("Phone must have at least 10 digits")
        if len(digits) == 10:
            return f"+91{digits}"
        return f"+{digits}" if not v.startswith("+") else v


class CustomerPhoneVerifyRequest(CustomerPhoneRequest):
    otp: str = Field(..., min_length=4, max_length=6)


def create_customer_access_token(customer_id: uuid.UUID) -> tuple[str, int]:
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_access_expire_minutes)
    payload = {
        "sub": str(customer_id),
        "type": "customer",
        "exp": expire,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, settings.jwt_access_expire_minutes * 60


def customer_auth_response(customer: Customer) -> CustomerAuthResponse:
    token, expires_in = create_customer_access_token(customer.id)
    return CustomerAuthResponse(
        access_token=token,
        expires_in=expires_in,
        customer=CustomerResponse.model_validate(customer),
    )


def store_customer_otp(phone: str) -> None:
    _CUSTOMER_OTP[phone.strip()] = "123456"


def verify_customer_otp(phone: str, otp: str) -> bool:
    return _CUSTOMER_OTP.get(phone.strip()) == otp


def clear_customer_otp_store() -> None:
    _CUSTOMER_OTP.clear()


def oauth_state_key(state: str) -> str:
    return f"oauth:customer:{state}"


async def save_oauth_state(
    redis_client,
    *,
    state: str,
    provider: str,
    redirect_uri: str,
    code_verifier: str | None,
) -> None:
    payload = {
        "provider": provider,
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier,
    }
    await redis_client.setex(oauth_state_key(state), 600, json.dumps(payload))


async def load_oauth_state(redis_client, state: str) -> dict | None:
    raw = await redis_client.get(oauth_state_key(state))
    if not raw:
        return None
    await redis_client.delete(oauth_state_key(state))
    return json.loads(raw)


async def upsert_customer_from_oauth(
    session: AsyncSession,
    provider: str,
    profile: OAuthProfile,
) -> tuple[Customer, bool]:
    result = await session.execute(
        select(CustomerOAuthIdentity).where(
            CustomerOAuthIdentity.provider == provider,
            CustomerOAuthIdentity.provider_user_id == profile.provider_user_id,
        )
    )
    identity = result.scalar_one_or_none()
    if identity:
        customer = await session.get(Customer, identity.customer_id)
        if not customer:
            raise ValueError("Linked customer not found")
        customer.name = profile.name or customer.name
        if profile.email and not customer.email:
            customer.email = profile.email
        if profile.avatar_url:
            customer.avatar_url = profile.avatar_url
        identity.profile = profile.raw
        if profile.email:
            identity.email = profile.email
        await session.flush()
        return customer, False

    customer = Customer(
        name=profile.name,
        email=profile.email,
        avatar_url=profile.avatar_url,
        status="active",
    )
    session.add(customer)
    await session.flush()

    session.add(
        CustomerOAuthIdentity(
            customer_id=customer.id,
            provider=provider,
            provider_user_id=profile.provider_user_id,
            email=profile.email,
            profile=profile.raw,
        )
    )
    await session.flush()
    return customer, True


async def upsert_customer_from_phone(session: AsyncSession, phone: str) -> tuple[Customer, bool]:
    result = await session.execute(select(Customer).where(Customer.phone == phone))
    existing = result.scalar_one_or_none()
    if existing:
        return existing, False

    customer = Customer(
        name=f"Customer {phone[-4:]}",
        phone=phone,
        status="active",
    )
    session.add(customer)
    await session.flush()
    return customer, True


def validate_oauth_provider(provider: str) -> str:
    normalized = provider.lower().strip()
    if normalized not in SUPPORTED_OAUTH_PROVIDERS:
        raise ValueError(f"Unsupported provider: {provider}")
    return normalized
