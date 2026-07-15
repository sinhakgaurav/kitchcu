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
    """Customer profile returned by `GET /customers/me` and embedded in auth responses."""

    id: uuid.UUID = Field(..., description="Customer UUID primary key.")
    name: str = Field(..., description="Customer display name.", examples=["Anjali Rao"])
    email: str | None = Field(default=None, description="Customer email (set via OAuth or optionally later).")
    phone: str | None = Field(default=None, description="Customer phone in E.164, if logged in via WhatsApp OTP.", examples=["+919123456789"])
    avatar_url: str | None = Field(default=None, description="Profile picture URL from the OAuth provider, if any.")
    upi_vpa: str | None = Field(default=None, description="Customer UPI VPA for refunds.", examples=["priya@okaxis"])
    upi_qr_url: str | None = Field(default=None, description="Uploaded UPI QR / scanner image URL.")
    bank_account_number_masked: str | None = Field(
        default=None, description="Masked bank account (last 4 digits only)."
    )
    bank_ifsc: str | None = Field(default=None, description="Bank IFSC for refunds.")
    bank_account_name: str | None = Field(default=None, description="Account holder name.")
    has_password: bool = Field(default=False, description="True when an optional account password is set.")
    status: str = Field(..., description="Customer account status.", examples=["active"])

    model_config = {"from_attributes": True}


class CustomerPayoutUpdateRequest(BaseModel):
    """Body for `PATCH /customers/me/payout` — UPI / bank instruments used for owner refunds."""

    upi_vpa: str | None = Field(default=None, max_length=100, description="UPI VPA, e.g. name@upi")
    bank_account_number: str | None = Field(default=None, max_length=34)
    bank_ifsc: str | None = Field(default=None, max_length=11)
    bank_account_name: str | None = Field(default=None, max_length=255)

    @field_validator("upi_vpa")
    @classmethod
    def validate_upi(cls, v: str | None) -> str | None:
        if v is None or not v.strip():
            return None
        v = v.strip()
        if "@" not in v:
            raise ValueError("UPI VPA must include @")
        return v

    @field_validator("bank_ifsc")
    @classmethod
    def normalize_ifsc(cls, v: str | None) -> str | None:
        if v is None or not v.strip():
            return None
        return v.strip().upper()


class CustomerAuthResponse(BaseModel):
    """Bearer token + profile returned after successful OAuth or WhatsApp OTP login.

    `access_token` is a JWT with `type: "customer"` and `sub` set to the customer UUID.
    """

    access_token: str = Field(
        ...,
        description='JWT bearer token, payload `{"sub": "<customer_id>", "type": "customer", "exp": ...}`.',
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    token_type: str = Field(default="bearer", description="Always `bearer`.", examples=["bearer"])
    expires_in: int = Field(..., description="Token lifetime in seconds from issuance.", examples=[3600])
    customer: CustomerResponse = Field(..., description="The authenticated customer's profile.")


class OAuthStartResponse(BaseModel):
    """Response for `GET /auth/customer/oauth/{provider}/start` — begin a social login."""

    provider: str = Field(..., description="Normalized OAuth provider id.", examples=["google"])
    state: str = Field(..., description="Opaque CSRF state token; echo it back unchanged in `/complete`.", examples=["a1b2c3d4"])
    authorization_url: str | None = Field(
        default=None, description="URL to redirect the customer to for provider consent. Null in dev mode."
    )
    dev_mode: bool = Field(
        default=False, description="True when OAuth client credentials are not configured and a simulated dev profile will be used."
    )


class OAuthCompleteRequest(BaseModel):
    """Body for `POST /auth/customer/oauth/{provider}/complete` — finishes a social login."""

    code: str = Field(..., description="Authorization code returned by the provider callback.", examples=["4/0AY0e-g7..."])
    state: str = Field(..., description="The `state` value returned from the `/start` call — validated against stored OAuth state.", examples=["a1b2c3d4"])
    redirect_uri: str = Field(..., description="Must exactly match the redirect_uri used in `/start`.", examples=["https://customer.kitchcu.in/oauth/callback"])


class CustomerPhoneRequest(BaseModel):
    """Body for `POST /auth/customer/whatsapp/request` — initiates WhatsApp OTP login."""

    phone: str = Field(
        ...,
        min_length=10,
        max_length=15,
        description="Customer WhatsApp/mobile number as 10 digits or E.164. Normalized to E.164 (+91XXXXXXXXXX).",
        examples=["9123456789"],
    )

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
    """Body for `POST /auth/customer/whatsapp/verify` — exchanges OTP for a customer JWT."""

    otp: str = Field(
        ...,
        min_length=4,
        max_length=6,
        description="One-time password sent via WhatsApp. Dev/staging value is always `123456`.",
        examples=["123456"],
    )


def create_customer_access_token(customer_id: uuid.UUID) -> tuple[str, int]:
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_access_expire_minutes)
    payload = {
        "sub": str(customer_id),
        "type": "customer",
        "exp": expire,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, settings.jwt_access_expire_minutes * 60


def _mask_account(account: str | None) -> str | None:
    if not account:
        return None
    digits = re.sub(r"\s+", "", account)
    if len(digits) <= 4:
        return "****"
    return f"{'*' * (len(digits) - 4)}{digits[-4:]}"


def customer_to_response(customer: Customer) -> CustomerResponse:
    return CustomerResponse(
        id=customer.id,
        name=customer.name,
        email=customer.email,
        phone=customer.phone,
        avatar_url=customer.avatar_url,
        upi_vpa=customer.upi_vpa,
        upi_qr_url=customer.upi_qr_url,
        bank_account_number_masked=_mask_account(customer.bank_account_number),
        bank_ifsc=customer.bank_ifsc,
        bank_account_name=customer.bank_account_name,
        has_password=bool(customer.password_hash),
        status=customer.status,
    )


def customer_auth_response(customer: Customer) -> CustomerAuthResponse:
    token, expires_in = create_customer_access_token(customer.id)
    return CustomerAuthResponse(
        access_token=token,
        expires_in=expires_in,
        customer=customer_to_response(customer),
    )


def update_customer_payout(customer: Customer, body: CustomerPayoutUpdateRequest) -> Customer:
    if body.upi_vpa is not None:
        customer.upi_vpa = body.upi_vpa
    if body.bank_account_number is not None:
        customer.bank_account_number = body.bank_account_number.strip() or None
    if body.bank_ifsc is not None:
        customer.bank_ifsc = body.bank_ifsc
    if body.bank_account_name is not None:
        customer.bank_account_name = body.bank_account_name.strip() or None
    return customer


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
