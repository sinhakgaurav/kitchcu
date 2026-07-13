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


class OwnerRegisterRequest(BaseModel):
    phone: str = Field(..., min_length=10, max_length=15)
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr | None = None

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, v: str) -> str:
        digits = re.sub(r"\D", "", v)
        if len(digits) < 10:
            raise ValueError("Phone must have at least 10 digits")
        if len(digits) == 10:
            return f"+91{digits}"
        return f"+{digits}" if not v.startswith("+") else v


class OwnerResponse(BaseModel):
    id: uuid.UUID
    phone: str
    name: str
    email: str | None
    subscription_tier: str
    subscription_status: str

    model_config = {"from_attributes": True}


class KitchenCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: str | None = None
    address_line: str
    city: str
    state: str
    pincode: str | None = None
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    free_delivery_radius_km: float = Field(default=3.0, gt=0, le=50)
    max_delivery_radius_km: float = Field(default=10.0, gt=0, le=100)
    delivery_fee_per_km: float = Field(default=10.0, ge=0, le=500)
    delivery_fee_flat_beyond: float = Field(default=0.0, ge=0, le=500)
    min_order_for_free_delivery: float | None = Field(default=None, ge=0)
    tracking_notify_interval_min: int = Field(default=5, ge=1, le=60)


class KitchenDeliverySettingsUpdate(BaseModel):
    free_delivery_radius_km: float | None = Field(default=None, gt=0, le=50)
    max_delivery_radius_km: float | None = Field(default=None, gt=0, le=100)
    delivery_fee_per_km: float | None = Field(default=None, ge=0, le=500)
    delivery_fee_flat_beyond: float | None = Field(default=None, ge=0, le=500)
    min_order_for_free_delivery: float | None = Field(default=None, ge=0)
    tracking_notify_interval_min: int | None = Field(default=None, ge=1, le=60)


class KitchenResponse(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    code: str
    name: str
    city: str | None
    state: str | None
    status: str
    free_delivery_radius_km: float
    max_delivery_radius_km: float
    delivery_fee_per_km: float
    delivery_fee_flat_beyond: float
    min_order_for_free_delivery: float | None
    tracking_notify_interval_min: int
    latitude: float
    longitude: float

    model_config = {"from_attributes": True}


class KitchenPublicResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    city: str | None
    state: str | None
    status: str

    model_config = {"from_attributes": True}


class KitchenNearbyResponse(KitchenPublicResponse):
    distance_km: float
    latitude: float
    longitude: float
    has_veg: bool = False
    has_non_veg: bool = False
    has_live_capture: bool = False
    is_live_now: bool = False


class KitchenNearbyListResponse(BaseModel):
    kitchens: list[KitchenNearbyResponse]
    total: int
    customer_latitude: float
    customer_longitude: float
    sort: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class OTPRequest(BaseModel):
    phone: str


class OTPVerifyRequest(BaseModel):
    phone: str
    otp: str = Field(..., min_length=4, max_length=6)


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
        latitude=float(row.lat),
        longitude=float(row.lng),
    )


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
    if data.tracking_notify_interval_min is not None:
        kitchen.tracking_notify_interval_min = data.tracking_notify_interval_min
    if kitchen.free_delivery_radius_km > kitchen.max_delivery_radius_km:
        raise ValueError("free_delivery_radius_km cannot exceed max_delivery_radius_km")
    await session.flush()
    return kitchen


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
