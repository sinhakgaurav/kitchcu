"""Customer profile edit, optional password, and address book."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime

import bcrypt
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Customer, CustomerAddress
from app.customer_schemas import verify_customer_otp


class CustomerProfileUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    avatar_url: str | None = Field(default=None, max_length=2000)


class CustomerPasswordChangeRequest(BaseModel):
    """Set or change optional password. Requires WhatsApp OTP when a phone is linked."""

    new_password: str = Field(..., min_length=8, max_length=72)
    current_password: str | None = Field(default=None, max_length=72)
    otp: str | None = Field(default=None, min_length=4, max_length=6)


class CustomerAddressCreateRequest(BaseModel):
    label: str = Field(default="Home", min_length=1, max_length=64)
    address_line: str = Field(..., min_length=3, max_length=500)
    city: str = Field(..., min_length=2, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    pincode: str | None = Field(default=None, max_length=12)
    landmark: str | None = Field(default=None, max_length=255)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    is_default: bool = False

    @field_validator("pincode")
    @classmethod
    def normalize_pin(cls, v: str | None) -> str | None:
        if v is None or not str(v).strip():
            return None
        digits = re.sub(r"\D", "", v)
        return digits or None


class CustomerAddressResponse(BaseModel):
    id: uuid.UUID
    label: str
    address_line: str
    city: str
    state: str | None
    pincode: str | None
    landmark: str | None
    latitude: float | None
    longitude: float | None
    is_default: bool
    created_at: datetime

    model_config = {"from_attributes": True}


def address_to_response(addr: CustomerAddress) -> CustomerAddressResponse:
    return CustomerAddressResponse(
        id=addr.id,
        label=addr.label,
        address_line=addr.address_line,
        city=addr.city,
        state=addr.state,
        pincode=addr.pincode,
        landmark=addr.landmark,
        latitude=float(addr.latitude) if addr.latitude is not None else None,
        longitude=float(addr.longitude) if addr.longitude is not None else None,
        is_default=bool(addr.is_default),
        created_at=addr.created_at,
    )


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt()).decode()


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode()[:72], password_hash.encode())
    except ValueError:
        return False


async def update_customer_profile(
    customer: Customer,
    body: CustomerProfileUpdateRequest,
) -> Customer:
    if body.name is not None:
        customer.name = body.name.strip()
    if body.email is not None:
        email = body.email.strip() or None
        customer.email = email
    if body.avatar_url is not None:
        customer.avatar_url = body.avatar_url.strip() or None
    return customer


async def change_customer_password(
    customer: Customer,
    body: CustomerPasswordChangeRequest,
) -> None:
    if customer.password_hash:
        if not body.current_password or not _verify_password(body.current_password, customer.password_hash):
            # Allow OTP override when phone linked
            if not (customer.phone and body.otp and verify_customer_otp(customer.phone, body.otp)):
                raise ValueError("Current password is incorrect (or provide WhatsApp OTP)")
    elif customer.phone:
        if not body.otp or not verify_customer_otp(customer.phone, body.otp):
            raise ValueError("WhatsApp OTP required to set a password")
    customer.password_hash = _hash_password(body.new_password)


async def list_addresses(session: AsyncSession, customer_id: uuid.UUID) -> list[CustomerAddress]:
    result = await session.execute(
        select(CustomerAddress)
        .where(CustomerAddress.customer_id == customer_id)
        .order_by(CustomerAddress.is_default.desc(), CustomerAddress.created_at.desc())
    )
    return list(result.scalars().all())


async def create_address(
    session: AsyncSession,
    customer_id: uuid.UUID,
    body: CustomerAddressCreateRequest,
) -> CustomerAddress:
    if body.is_default:
        await session.execute(
            update(CustomerAddress)
            .where(CustomerAddress.customer_id == customer_id)
            .values(is_default=False)
        )
    addr = CustomerAddress(
        customer_id=customer_id,
        label=body.label.strip(),
        address_line=body.address_line.strip(),
        city=body.city.strip(),
        state=body.state.strip() if body.state else None,
        pincode=body.pincode,
        landmark=body.landmark.strip() if body.landmark else None,
        latitude=body.latitude,
        longitude=body.longitude,
        is_default=body.is_default,
    )
    session.add(addr)
    await session.flush()
    return addr


async def update_address(
    session: AsyncSession,
    customer_id: uuid.UUID,
    address_id: uuid.UUID,
    body: CustomerAddressCreateRequest,
) -> CustomerAddress:
    addr = await session.get(CustomerAddress, address_id)
    if not addr or addr.customer_id != customer_id:
        raise ValueError("Address not found")
    if body.is_default:
        await session.execute(
            update(CustomerAddress)
            .where(CustomerAddress.customer_id == customer_id)
            .values(is_default=False)
        )
    addr.label = body.label.strip()
    addr.address_line = body.address_line.strip()
    addr.city = body.city.strip()
    addr.state = body.state.strip() if body.state else None
    addr.pincode = body.pincode
    addr.landmark = body.landmark.strip() if body.landmark else None
    addr.latitude = body.latitude
    addr.longitude = body.longitude
    addr.is_default = body.is_default
    addr.updated_at = datetime.now(UTC)
    await session.flush()
    return addr


async def delete_address(
    session: AsyncSession,
    customer_id: uuid.UUID,
    address_id: uuid.UUID,
) -> None:
    addr = await session.get(CustomerAddress, address_id)
    if not addr or addr.customer_id != customer_id:
        raise ValueError("Address not found")
    await session.delete(addr)
    await session.flush()
