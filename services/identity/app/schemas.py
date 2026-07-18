import re
import uuid
from datetime import UTC, datetime, timedelta

from geoalchemy2.elements import WKTElement
from jose import jwt
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Kitchen, Owner
from ckac_common.config import get_settings

settings = get_settings()

CITY_CODES: dict[str, str] = {
    "pune": "PNQ",
    "mumbai": "BOM",
    "bangalore": "BLR",
    "bengaluru": "BLR",
    "delhi": "DEL",
    "hyderabad": "HYD",
    "chennai": "MAA",
    "kolkata": "CCU",
}


def normalize_india_phone(v: str) -> str:
    """Normalize 10-digit India mobile or E.164 into +91XXXXXXXXXX."""
    digits = re.sub(r"\D", "", v or "")
    if len(digits) < 10:
        raise ValueError("Phone must have at least 10 digits")
    if len(digits) == 10:
        return f"+91{digits}"
    if len(digits) == 12 and digits.startswith("91"):
        return f"+{digits}"
    if 10 < len(digits) <= 15:
        return f"+{digits}"
    raise ValueError("Invalid phone number")


class OwnerRegisterRequest(BaseModel):
    """Body for `POST /owners/register` — creates a kitchCU owner account."""

    phone: str = Field(
        ...,
        min_length=10,
        max_length=15,
        description=(
            "India mobile as 10 digits or E.164 (+91...). Normalized to E.164 "
            "(+91XXXXXXXXXX) and used as the unique owner login identifier."
        ),
        examples=["9876543210"],
    )
    name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Owner's display name shown across owner dashboards and invoices.",
        examples=["Priya Sharma"],
    )
    email: EmailStr | None = Field(
        default=None,
        description="Optional owner email for billing receipts and platform notices.",
        examples=["priya@kitchcu.dev"],
    )

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, v: str) -> str:
        return normalize_india_phone(v)


class OwnerResponse(BaseModel):
    """Owner profile returned by registration and `GET /owners/me`."""

    id: uuid.UUID = Field(..., description="Owner UUID primary key.")
    phone: str = Field(..., description="Owner phone in E.164 format.", examples=["+919876543210"])
    name: str = Field(..., description="Owner display name.", examples=["Priya Sharma"])
    email: str | None = Field(default=None, description="Owner email, if provided.")
    subscription_tier: str = Field(
        ..., description="Owner SaaS subscription plan tier.", examples=["trial", "starter", "growth"]
    )
    subscription_status: str = Field(
        ..., description="Current subscription lifecycle status.", examples=["trial", "active", "past_due"]
    )

    model_config = {"from_attributes": True}


class KitchenCreateRequest(BaseModel):
    """Body for `POST /kitchens` — onboards a new cloud kitchen for the authenticated owner."""

    name: str = Field(
        ..., min_length=2, max_length=255, description="Kitchen brand name shown to customers.", examples=["Spice Route Kitchen"]
    )
    description: str | None = Field(
        default=None, description="Short kitchen bio/tagline shown on the public kitchen page.", examples=["Home-style North Indian tiffins"]
    )
    address_line: str = Field(..., description="Street address of the kitchen (not shown to customers by default).", examples=["221B, MG Road"])
    city: str = Field(..., description="City name — used to derive the kitchen code prefix.", examples=["Pune"])
    state: str = Field(..., description="State name.", examples=["Maharashtra"])
    pincode: str | None = Field(default=None, description="Postal PIN code.", examples=["411001"])
    latitude: float = Field(..., ge=-90, le=90, description="Kitchen latitude (WGS84) for delivery radius + discovery.", examples=[18.5204])
    longitude: float = Field(..., ge=-180, le=180, description="Kitchen longitude (WGS84) for delivery radius + discovery.", examples=[73.8567])
    free_delivery_radius_km: float = Field(
        default=3.0, gt=0, le=50, description="Radius (km) within which delivery is free.", examples=[3.0]
    )
    max_delivery_radius_km: float = Field(
        default=10.0, gt=0, le=100, description="Maximum radius (km) the kitchen delivers to; must be >= free radius.", examples=[10.0]
    )
    delivery_fee_per_km: float = Field(
        default=10.0, ge=0, le=500, description="Delivery fee charged per km beyond the free radius.", examples=[10.0]
    )
    delivery_fee_flat_beyond: float = Field(
        default=0.0, ge=0, le=500, description="Flat delivery fee add-on applied beyond the free radius.", examples=[0.0]
    )
    min_order_for_free_delivery: float | None = Field(
        default=None, ge=0, description="Order subtotal (INR) at or above which delivery becomes free, regardless of distance.", examples=[299.0]
    )
    tracking_notify_interval_min: int = Field(
        default=5, ge=1, le=60, description="Minutes between owner→customer delivery tracking notifications.", examples=[5]
    )


class KitchenDeliverySettingsUpdate(BaseModel):
    """Partial-update body for `PATCH /kitchens/{kitchen_id}/delivery-settings`. All fields optional."""

    free_delivery_radius_km: float | None = Field(
        default=None, gt=0, le=50, description="New free-delivery radius (km). Omit to leave unchanged.", examples=[3.0]
    )
    max_delivery_radius_km: float | None = Field(
        default=None, gt=0, le=100, description="New max delivery radius (km); must stay >= free radius. Omit to leave unchanged.", examples=[12.0]
    )
    delivery_fee_per_km: float | None = Field(
        default=None, ge=0, le=500, description="New per-km delivery fee beyond the free radius. Omit to leave unchanged.", examples=[12.0]
    )
    delivery_fee_flat_beyond: float | None = Field(
        default=None, ge=0, le=500, description="New flat delivery fee add-on beyond the free radius. Omit to leave unchanged.", examples=[10.0]
    )
    min_order_for_free_delivery: float | None = Field(
        default=None, ge=0, description="Min cart (INR) so kitchen subsidizes extended-range delivery. Omit to leave unchanged.", examples=[349.0]
    )
    delivery_subsidy_percent: float | None = Field(
        default=None,
        ge=0,
        le=100,
        description="When beyond max radius and min order met, % of logistics cost kitchen bears (customer pays the rest).",
        examples=[50.0],
    )
    tracking_notify_interval_min: int | None = Field(
        default=None, ge=1, le=60, description="New tracking notification interval in minutes. Omit to leave unchanged.", examples=[10]
    )


class KitchenWhatsAppIntegrationResponse(BaseModel):
    """Owner view of Meta WhatsApp Business Cloud API linkage for inbound F01 orders."""

    kitchen_id: uuid.UUID
    whatsapp_phone_id: str | None = Field(
        default=None,
        description="Meta WhatsApp Cloud API phone_number_id used to route inbound webhooks.",
    )
    whatsapp_display_phone: str | None = Field(
        default=None,
        description="Human-readable E.164 business number shown in the owner dashboard.",
    )
    connected: bool = Field(..., description="True when whatsapp_phone_id is set.")
    platform_secrets_note: str = Field(
        default=(
            "Meta App Secret and Verify Token are platform-managed in Super Admin → API Keys. "
            "This kitchen only needs its Phone Number ID."
        ),
    )


class KitchenWhatsAppIntegrationUpdate(BaseModel):
    """Connect or disconnect Meta WhatsApp Business for this kitchen."""

    whatsapp_phone_id: str | None = Field(
        default=None,
        max_length=100,
        description="Meta phone_number_id. Pass null with clear=true to disconnect.",
    )
    whatsapp_display_phone: str | None = Field(
        default=None,
        max_length=20,
        description="Optional E.164 display number, e.g. +919876543210.",
    )
    clear: bool = Field(
        default=False,
        description="When true, clears phone_number_id and display phone (disconnect).",
    )

    @field_validator("whatsapp_phone_id")
    @classmethod
    def normalize_phone_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("whatsapp_display_phone")
    @classmethod
    def normalize_display_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().replace(" ", "")
        if not cleaned:
            return None
        if not cleaned.startswith("+"):
            digits = "".join(c for c in cleaned if c.isdigit())
            if len(digits) == 10:
                return f"+91{digits}"
            return f"+{digits}"
        return cleaned


class KitchenBrandedPageSettings(BaseModel):
    """Owner-controlled kitchen-first storefront (menu → order → bill) with Powered-by kitchCU."""

    enabled: bool = Field(
        default=False,
        description="When true, the public branded storefront at `/k/{code}` is published for customers.",
    )
    tagline: str | None = Field(
        default=None,
        max_length=160,
        description="Optional short line under the kitchen name on the branded page.",
        examples=["Home-style thalis · live-capture menu"],
    )
    accent_color: str | None = Field(
        default=None,
        max_length=7,
        description="Optional hex accent for the branded header (e.g. `#0F766E`).",
        examples=["#0F766E"],
    )

    @field_validator("tagline")
    @classmethod
    def normalize_tagline(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("accent_color")
    @classmethod
    def normalize_accent(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", cleaned):
            raise ValueError("accent_color must be a 6-digit hex color like #0F766E")
        return cleaned.upper()


class KitchenBrandedPageUpdate(BaseModel):
    """Partial update for `PATCH /kitchens/{kitchen_id}/branded-page`."""

    enabled: bool | None = Field(
        default=None,
        description="Publish or unpublish the branded storefront. Omit to leave unchanged.",
    )
    tagline: str | None = Field(
        default=None,
        max_length=160,
        description="Tagline under the kitchen name. Pass empty string to clear.",
    )
    accent_color: str | None = Field(
        default=None,
        max_length=7,
        description="Hex accent. Pass empty string to clear.",
    )

    @field_validator("tagline")
    @classmethod
    def normalize_tagline(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()

    @field_validator("accent_color")
    @classmethod
    def normalize_accent(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return ""
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", cleaned):
            raise ValueError("accent_color must be a 6-digit hex color like #0F766E")
        return cleaned.upper()


class KitchenResponse(BaseModel):
    """Full kitchen record returned to the owning owner (create, list-mine, update)."""

    id: uuid.UUID = Field(..., description="Kitchen UUID primary key.")
    owner_id: uuid.UUID = Field(..., description="Owning owner's UUID.")
    code: str = Field(..., description="Unique kitchen code: CK + city(3) + seq(3).", examples=["CKPNQ001"])
    name: str = Field(..., description="Kitchen brand name.", examples=["Spice Route Kitchen"])
    city: str | None = Field(default=None, description="Kitchen city.", examples=["Pune"])
    state: str | None = Field(default=None, description="Kitchen state.", examples=["Maharashtra"])
    status: str = Field(..., description="Kitchen lifecycle status.", examples=["active", "suspended", "pending_verification"])
    free_delivery_radius_km: float = Field(..., description="Free delivery radius in km.")
    max_delivery_radius_km: float = Field(..., description="Maximum delivery radius in km.")
    delivery_fee_per_km: float = Field(..., description="Delivery fee per km beyond the free radius.")
    delivery_fee_flat_beyond: float = Field(..., description="Flat delivery fee add-on beyond the free radius.")
    min_order_for_free_delivery: float | None = Field(default=None, description="Order subtotal (INR) for automatic free delivery.")
    tracking_notify_interval_min: int = Field(..., description="Minutes between delivery tracking notifications.")
    address_line: str | None = Field(default=None, description="Kitchen street address (owner-only).")
    pincode: str | None = Field(default=None, description="Kitchen postal PIN code.")
    latitude: float = Field(..., description="Kitchen latitude (WGS84).", examples=[18.5204])
    longitude: float = Field(..., description="Kitchen longitude (WGS84).", examples=[73.8567])
    branded_page: KitchenBrandedPageSettings = Field(
        default_factory=KitchenBrandedPageSettings,
        description="Kitchen-first branded storefront settings (menu/order/bill + Powered by kitchCU).",
    )

    model_config = {"from_attributes": True}


class KitchenPublicResponse(BaseModel):
    """Minimal public kitchen record — safe to expose to unauthenticated customers."""

    id: uuid.UUID = Field(..., description="Kitchen UUID primary key.")
    code: str = Field(..., description="Unique kitchen code.", examples=["CKPNQ001"])
    name: str = Field(..., description="Kitchen brand name.", examples=["Spice Route Kitchen"])
    city: str | None = Field(default=None, description="Kitchen city.", examples=["Pune"])
    state: str | None = Field(default=None, description="Kitchen state.", examples=["Maharashtra"])
    status: str = Field(..., description="Kitchen lifecycle status.", examples=["active"])
    description: str | None = Field(
        default=None,
        description="Short kitchen bio shown on the branded storefront.",
    )
    branded_page: KitchenBrandedPageSettings = Field(
        default_factory=KitchenBrandedPageSettings,
        description="Kitchen-first storefront settings (Powered by kitchCU).",
    )

    model_config = {"from_attributes": True}


class KitchenNearbyResponse(KitchenPublicResponse):
    """A public kitchen entry with distance + discovery signals, for the nearby-search endpoint."""

    distance_km: float = Field(..., description="Great-circle distance from the query point, in km.", examples=[1.42])
    latitude: float = Field(..., description="Kitchen latitude (WGS84).", examples=[18.5204])
    longitude: float = Field(..., description="Kitchen longitude (WGS84).", examples=[73.8567])
    has_veg: bool = Field(default=False, description="True if the kitchen has an active veg-category dish.")
    has_non_veg: bool = Field(default=False, description="True if the kitchen has an active non-veg-category dish.")
    has_live_capture: bool = Field(default=False, description="True if the kitchen has a live-capture (non-stock-photo) hero dish image.")
    is_live_now: bool = Field(default=False, description="True if the kitchen is currently streaming a live prep session.")


class KitchenNearbyListResponse(BaseModel):
    """Response for `GET /kitchens/public/nearby` — a distance-sorted page of kitchens."""

    kitchens: list[KitchenNearbyResponse] = Field(..., description="Kitchens within `max_km`, ordered by `sort`.")
    total: int = Field(..., description="Number of kitchens returned in this response.", examples=[8])
    customer_latitude: float = Field(..., description="Echo of the query latitude used for distance calc.", examples=[18.5204])
    customer_longitude: float = Field(..., description="Echo of the query longitude used for distance calc.", examples=[73.8567])
    sort: str = Field(..., description="Sort order applied.", examples=["asc", "desc"])


class TokenResponse(BaseModel):
    """Bearer token issued after successful owner OTP verification.

    `access_token` is a JWT with `type: "owner"` and `sub` set to the owner UUID.
    Send it as `Authorization: Bearer <access_token>` on subsequent owner-scoped APIs.
    """

    access_token: str = Field(
        ...,
        description='JWT bearer token, payload `{"sub": "<owner_id>", "phone": "...", "type": "owner", "exp": ...}`.',
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    token_type: str = Field(default="bearer", description="Always `bearer`.", examples=["bearer"])
    expires_in: int = Field(..., description="Token lifetime in seconds from issuance.", examples=[3600])


class OTPRequest(BaseModel):
    """Body for `POST /auth/otp/request` — initiates owner login."""

    phone: str = Field(
        ...,
        description="Owner phone (10-digit India mobile or E.164). Dev mode always issues OTP 123456.",
        examples=["9876543210"],
    )

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, v: str) -> str:
        return normalize_india_phone(v)


class OTPVerifyRequest(BaseModel):
    """Body for `POST /auth/otp/verify` — exchanges OTP for an owner JWT."""

    phone: str = Field(..., description="Same phone used in the OTP request.", examples=["9876543210"])
    otp: str = Field(
        ...,
        min_length=4,
        max_length=6,
        description="One-time password. Dev/staging value is always `123456`.",
        examples=["123456"],
    )

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, v: str) -> str:
        return normalize_india_phone(v)


def create_access_token(owner_id: uuid.UUID, phone: str) -> TokenResponse:
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_access_expire_minutes)
    payload = {
        "sub": str(owner_id),
        "phone": phone,
        "type": "owner",
        "exp": expire,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_access_expire_minutes * 60,
    )


async def generate_kitchen_code(session: AsyncSession, city: str) -> str:
    city_key = city.strip().lower()
    city_code = CITY_CODES.get(city_key, city_key[:3].upper().ljust(3, "X")[:3])
    prefix = f"CK{city_code}"
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
        {"lock_key": f"kitchen_code:{prefix}"},
    )
    result = await session.execute(
        select(func.count()).select_from(Kitchen).where(Kitchen.code.like(f"{prefix}%"))
    )
    seq = (result.scalar() or 0) + 1
    return f"{prefix}{seq:03d}"


async def register_owner(session: AsyncSession, data: OwnerRegisterRequest) -> Owner:
    existing = await session.execute(select(Owner).where(Owner.phone == data.phone))
    if existing.scalar_one_or_none():
        raise ValueError("Owner with this phone already exists")

    owner = Owner(
        phone=data.phone,
        name=data.name,
        email=str(data.email) if data.email else None,
        subscription_status="trial",
    )
    session.add(owner)
    await session.flush()
    return owner


async def create_kitchen(
    session: AsyncSession, owner_id: uuid.UUID, data: KitchenCreateRequest
) -> Kitchen:
    code = await generate_kitchen_code(session, data.city)
    kitchen = Kitchen(
        owner_id=owner_id,
        code=code,
        name=data.name,
        description=data.description,
        address_line=data.address_line,
        city=data.city,
        state=data.state,
        pincode=data.pincode,
        location=WKTElement(f"POINT({data.longitude} {data.latitude})", srid=4326),
        free_delivery_radius_km=data.free_delivery_radius_km,
        max_delivery_radius_km=data.max_delivery_radius_km,
        delivery_fee_per_km=data.delivery_fee_per_km,
        delivery_fee_flat_beyond=data.delivery_fee_flat_beyond,
        min_order_for_free_delivery=data.min_order_for_free_delivery,
        tracking_notify_interval_min=data.tracking_notify_interval_min,
        status="active",
    )
    session.add(kitchen)
    await session.flush()
    return kitchen


def branded_page_from_settings(settings_blob: dict | None) -> KitchenBrandedPageSettings:
    blob = settings_blob if isinstance(settings_blob, dict) else {}
    raw = blob.get("branded_page") if isinstance(blob.get("branded_page"), dict) else {}
    try:
        return KitchenBrandedPageSettings.model_validate(raw or {})
    except Exception:
        return KitchenBrandedPageSettings()


def kitchen_to_public_response(kitchen: Kitchen) -> KitchenPublicResponse:
    return KitchenPublicResponse(
        id=kitchen.id,
        code=kitchen.code,
        name=kitchen.name,
        city=kitchen.city,
        state=kitchen.state,
        status=kitchen.status,
        description=kitchen.description,
        branded_page=branded_page_from_settings(
            kitchen.settings if isinstance(kitchen.settings, dict) else {}
        ),
    )


async def kitchen_to_response(session: AsyncSession, kitchen: Kitchen) -> KitchenResponse:
    result = await session.execute(
        text(
            "SELECT ST_Y(location::geometry) AS lat, ST_X(location::geometry) AS lng "
            "FROM ckac_identity.kitchens WHERE id = :id"
        ),
        {"id": kitchen.id},
    )
    row = result.one()
    return KitchenResponse(
        id=kitchen.id,
        owner_id=kitchen.owner_id,
        code=kitchen.code,
        name=kitchen.name,
        city=kitchen.city,
        state=kitchen.state,
        status=kitchen.status,
        free_delivery_radius_km=float(kitchen.free_delivery_radius_km),
        max_delivery_radius_km=float(kitchen.max_delivery_radius_km),
        delivery_fee_per_km=float(kitchen.delivery_fee_per_km),
        delivery_fee_flat_beyond=float(kitchen.delivery_fee_flat_beyond),
        min_order_for_free_delivery=(
            float(kitchen.min_order_for_free_delivery)
            if kitchen.min_order_for_free_delivery is not None
            else None
        ),
        tracking_notify_interval_min=int(kitchen.tracking_notify_interval_min),
        address_line=kitchen.address_line,
        pincode=kitchen.pincode,
        latitude=float(row.lat),
        longitude=float(row.lng),
        branded_page=branded_page_from_settings(
            kitchen.settings if isinstance(kitchen.settings, dict) else {}
        ),
    )


async def update_kitchen_branded_page(
    session: AsyncSession,
    kitchen: Kitchen,
    data: KitchenBrandedPageUpdate,
    publisher: "EventPublisher | None" = None,
) -> Kitchen:
    from sqlalchemy.orm.attributes import flag_modified

    from ckac_common.auth import stream_key
    from ckac_common.event_bus import EventPublisher

    settings_blob = dict(kitchen.settings) if isinstance(kitchen.settings, dict) else {}
    current = branded_page_from_settings(settings_blob).model_dump()

    if data.enabled is not None:
        current["enabled"] = data.enabled
    if "tagline" in data.model_fields_set:
        current["tagline"] = data.tagline or None
    if "accent_color" in data.model_fields_set:
        current["accent_color"] = data.accent_color or None

    settings_blob["branded_page"] = KitchenBrandedPageSettings.model_validate(current).model_dump()
    kitchen.settings = settings_blob
    flag_modified(kitchen, "settings")
    await session.flush()

    if publisher:
        event = EventPublisher.build(
            event_type="kitchen.branded_page.updated",
            aggregate_type="kitchen",
            aggregate_id=str(kitchen.id),
            producer="identity-service",
            payload={
                "kitchen_id": str(kitchen.id),
                "kitchen_code": kitchen.code,
                "enabled": bool(current["enabled"]),
            },
        )
        await publisher.publish(stream_key("identity", "kitchen"), event, session=session)

    return kitchen


async def update_kitchen_delivery_settings(
    session: AsyncSession,
    kitchen: Kitchen,
    data: KitchenDeliverySettingsUpdate,
) -> Kitchen:
    if data.free_delivery_radius_km is not None:
        kitchen.free_delivery_radius_km = data.free_delivery_radius_km
    if data.max_delivery_radius_km is not None:
        kitchen.max_delivery_radius_km = data.max_delivery_radius_km
    if data.delivery_fee_per_km is not None:
        kitchen.delivery_fee_per_km = data.delivery_fee_per_km
    if data.delivery_fee_flat_beyond is not None:
        kitchen.delivery_fee_flat_beyond = data.delivery_fee_flat_beyond
    if data.min_order_for_free_delivery is not None:
        kitchen.min_order_for_free_delivery = data.min_order_for_free_delivery
    if data.delivery_subsidy_percent is not None:
        kitchen.delivery_subsidy_percent = data.delivery_subsidy_percent
    if data.tracking_notify_interval_min is not None:
        kitchen.tracking_notify_interval_min = data.tracking_notify_interval_min
    if kitchen.free_delivery_radius_km > kitchen.max_delivery_radius_km:
        raise ValueError("free_delivery_radius_km cannot exceed max_delivery_radius_km")
    await session.flush()
    return kitchen


def kitchen_whatsapp_to_response(kitchen: Kitchen) -> KitchenWhatsAppIntegrationResponse:
    settings_blob = kitchen.settings if isinstance(kitchen.settings, dict) else {}
    display = settings_blob.get("whatsapp_display_phone")
    phone_id = kitchen.whatsapp_phone_id
    return KitchenWhatsAppIntegrationResponse(
        kitchen_id=kitchen.id,
        whatsapp_phone_id=phone_id,
        whatsapp_display_phone=display if isinstance(display, str) else None,
        connected=bool(phone_id),
    )


async def get_kitchen_whatsapp_integration(
    session: AsyncSession,
    kitchen: Kitchen,
) -> KitchenWhatsAppIntegrationResponse:
    _ = session
    return kitchen_whatsapp_to_response(kitchen)


async def update_kitchen_whatsapp_integration(
    session: AsyncSession,
    kitchen: Kitchen,
    data: KitchenWhatsAppIntegrationUpdate,
    publisher: "EventPublisher | None" = None,
    *,
    enforce_module: bool = True,
) -> KitchenWhatsAppIntegrationResponse:
    from ckac_common.auth import stream_key
    from ckac_common.event_bus import EventPublisher
    from ckac_common.platform_config import require_kitchen_module

    # Super-admin ops may configure linkage even while the module kill-switch is off.
    if enforce_module:
        await require_kitchen_module(session, kitchen.id, "whatsapp")

    settings_blob = dict(kitchen.settings) if isinstance(kitchen.settings, dict) else {}

    if data.clear:
        kitchen.whatsapp_phone_id = None
        settings_blob.pop("whatsapp_display_phone", None)
    else:
        if data.whatsapp_phone_id is not None:
            conflict = await session.execute(
                select(Kitchen.id).where(
                    Kitchen.whatsapp_phone_id == data.whatsapp_phone_id,
                    Kitchen.id != kitchen.id,
                ).limit(1)
            )
            if conflict.scalar_one_or_none():
                raise ValueError("WhatsApp phone number ID is already linked to another kitchen")
            kitchen.whatsapp_phone_id = data.whatsapp_phone_id
        if "whatsapp_display_phone" in data.model_fields_set:
            if data.whatsapp_display_phone:
                settings_blob["whatsapp_display_phone"] = data.whatsapp_display_phone
            else:
                settings_blob.pop("whatsapp_display_phone", None)

    kitchen.settings = settings_blob
    from sqlalchemy.orm.attributes import flag_modified

    flag_modified(kitchen, "settings")
    await session.flush()

    if publisher:
        event = EventPublisher.build(
            event_type="kitchen.whatsapp.updated",
            aggregate_type="kitchen",
            aggregate_id=str(kitchen.id),
            producer="identity-service",
            payload={
                "kitchen_id": str(kitchen.id),
                "connected": bool(kitchen.whatsapp_phone_id),
                "whatsapp_phone_id": kitchen.whatsapp_phone_id,
            },
        )
        await publisher.publish(stream_key("identity", "kitchen"), event, session=session)

    return kitchen_whatsapp_to_response(kitchen)


async def list_kitchens_nearby(
    session: AsyncSession,
    *,
    latitude: float,
    longitude: float,
    limit: int = 20,
    max_km: float = 50.0,
    sort: str = "asc",
    diet: str | None = None,
    live_capture: bool | None = None,
    live_only: bool | None = None,
) -> list[KitchenNearbyResponse]:
    """Active kitchens within max_km, ordered by distance (asc = nearest first)."""
    order = "ASC" if sort.lower() != "desc" else "DESC"
    max_m = max_km * 1000.0
    limit = min(max(limit, 1), 100)

    diet_filter = ""
    params: dict = {"lat": latitude, "lng": longitude, "max_m": max_m, "lim": limit}
    if diet in ("veg", "non_veg", "vegan"):
        diet_filter = """
              AND EXISTS (
                    SELECT 1 FROM ckac_catalog.dishes d
                    INNER JOIN ckac_catalog.categories c ON c.id = d.category_id
                    WHERE d.kitchen_id = ckac_identity.kitchens.id
                      AND d.is_active = true
                      AND c.slug = :diet
              )
        """
        params["diet"] = diet
    if live_capture:
        diet_filter += """
              AND EXISTS (
                    SELECT 1 FROM ckac_catalog.dishes d
                    INNER JOIN ckac_catalog.dish_media m ON m.dish_id = d.id
                    WHERE d.kitchen_id = ckac_identity.kitchens.id
                      AND d.is_active = true
                      AND m.is_hero = true
                      AND m.is_live_capture = true
              )
        """
    if live_only:
        diet_filter += """
              AND EXISTS (
                    SELECT 1 FROM ckac_streaming.live_sessions s
                    INNER JOIN ckac_streaming.kitchen_stream_settings st ON st.kitchen_id = s.kitchen_id
                    WHERE s.kitchen_id = ckac_identity.kitchens.id
                      AND s.status = 'live'
                      AND st.live_sharing_enabled = true
              )
        """

    result = await session.execute(
        text(
            f"""
            SELECT
                id,
                code,
                name,
                city,
                state,
                status,
                ST_Y(location::geometry) AS lat,
                ST_X(location::geometry) AS lng,
                ST_Distance(
                    location,
                    ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography
                ) / 1000.0 AS distance_km,
                EXISTS (
                    SELECT 1 FROM ckac_catalog.dishes d
                    INNER JOIN ckac_catalog.categories c ON c.id = d.category_id
                    WHERE d.kitchen_id = ckac_identity.kitchens.id
                      AND d.is_active = true AND c.slug = 'veg'
                ) AS has_veg,
                EXISTS (
                    SELECT 1 FROM ckac_catalog.dishes d
                    INNER JOIN ckac_catalog.categories c ON c.id = d.category_id
                    WHERE d.kitchen_id = ckac_identity.kitchens.id
                      AND d.is_active = true AND c.slug = 'non_veg'
                ) AS has_non_veg,
                EXISTS (
                    SELECT 1 FROM ckac_catalog.dishes d
                    INNER JOIN ckac_catalog.dish_media m ON m.dish_id = d.id
                    WHERE d.kitchen_id = ckac_identity.kitchens.id
                      AND d.is_active = true
                      AND m.is_hero = true AND m.is_live_capture = true
                ) AS has_live_capture,
                EXISTS (
                    SELECT 1 FROM ckac_streaming.live_sessions s
                    INNER JOIN ckac_streaming.kitchen_stream_settings st ON st.kitchen_id = s.kitchen_id
                    WHERE s.kitchen_id = ckac_identity.kitchens.id
                      AND s.status = 'live'
                      AND st.live_sharing_enabled = true
                ) AS is_live_now
            FROM ckac_identity.kitchens
            WHERE status = 'active'
              AND ST_DWithin(
                    location,
                    ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
                    :max_m
                  )
              {diet_filter}
            ORDER BY distance_km {order}
            LIMIT :lim
            """
        ),
        params,
    )
    rows = result.all()
    return [
        KitchenNearbyResponse(
            id=row.id,
            code=row.code,
            name=row.name,
            city=row.city,
            state=row.state,
            status=row.status,
            latitude=float(row.lat),
            longitude=float(row.lng),
            distance_km=round(float(row.distance_km), 2),
            has_veg=bool(row.has_veg),
            has_non_veg=bool(row.has_non_veg),
            has_live_capture=bool(row.has_live_capture),
            is_live_now=bool(row.is_live_now),
        )
        for row in rows
    ]
