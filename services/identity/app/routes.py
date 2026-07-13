import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Kitchen, Owner
from app.schemas import (
    KitchenCreateRequest,
    KitchenDeliverySettingsUpdate,
    KitchenNearbyListResponse,
    KitchenPublicResponse,
    KitchenResponse,
    OTPRequest,
    OTPVerifyRequest,
    OwnerRegisterRequest,
    OwnerResponse,
    TokenResponse,
    create_access_token,
    create_kitchen,
    kitchen_to_response,
    list_kitchens_nearby,
    register_owner,
    update_kitchen_delivery_settings,
)
from ckac_common.auth import stream_key
from ckac_common.config import get_settings
from ckac_common.database import get_db
from ckac_common.event_bus import EventPublisher

router = APIRouter()
security = HTTPBearer(auto_error=False)
settings = get_settings()

_DEV_OTP: dict[str, str] = {}


def get_publisher() -> EventPublisher:
    from app.main import event_publisher

    return event_publisher


async def get_current_owner(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Owner:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(
            credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        owner_id = uuid.UUID(payload["sub"])
    except (JWTError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    result = await session.execute(select(Owner).where(Owner.id == owner_id))
    owner = result.scalar_one_or_none()
    if not owner:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Owner not found")
    return owner


@router.post("/auth/otp/request", status_code=status.HTTP_202_ACCEPTED)
async def request_otp(body: OTPRequest) -> dict[str, str]:
    """Request OTP for owner login. Dev mode: OTP is always 123456."""
    phone = body.phone.strip()
    _DEV_OTP[phone] = "123456"
    return {"message": "OTP sent", "dev_hint": "Use 123456 in development"}


@router.post("/auth/otp/verify", response_model=TokenResponse)
async def verify_otp(
    body: OTPVerifyRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    expected = _DEV_OTP.get(body.phone.strip())
    if expected != body.otp:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid OTP")

    result = await session.execute(select(Owner).where(Owner.phone == body.phone.strip()))
    owner = result.scalar_one_or_none()
    if not owner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Owner not registered")
    return create_access_token(owner.id, owner.phone)


@router.post("/owners/register", response_model=OwnerResponse, status_code=status.HTTP_201_CREATED)
async def owner_register(
    body: OwnerRegisterRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Owner:
    try:
        owner = await register_owner(session, body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return owner


@router.get("/owners/me", response_model=OwnerResponse)
async def owner_me(owner: Annotated[Owner, Depends(get_current_owner)]) -> Owner:
    return owner


@router.post("/kitchens", response_model=KitchenResponse, status_code=status.HTTP_201_CREATED)
async def kitchen_create(
    body: KitchenCreateRequest,
    owner: Annotated[Owner, Depends(get_current_owner)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> KitchenResponse:
    kitchen = await create_kitchen(session, owner.id, body)
    event = EventPublisher.build(
        event_type="kitchen.created",
        aggregate_type="kitchen",
        aggregate_id=str(kitchen.id),
        producer="identity-service",
        payload={
            "kitchen_id": str(kitchen.id),
            "owner_id": str(owner.id),
            "code": kitchen.code,
            "city": kitchen.city,
        },
    )
    await publisher.publish(stream_key("identity", "kitchen"), event, session=session)
    return await kitchen_to_response(session, kitchen)


@router.get("/kitchens/me", response_model=list[KitchenResponse])
async def kitchens_me(
    owner: Annotated[Owner, Depends(get_current_owner)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[KitchenResponse]:
    result = await session.execute(select(Kitchen).where(Kitchen.owner_id == owner.id))
    kitchens = result.scalars().all()
    return [await kitchen_to_response(session, k) for k in kitchens]


@router.patch("/kitchens/{kitchen_id}/delivery-settings", response_model=KitchenResponse)
async def kitchen_delivery_settings_update(
    kitchen_id: uuid.UUID,
    body: KitchenDeliverySettingsUpdate,
    owner: Annotated[Owner, Depends(get_current_owner)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> KitchenResponse:
    result = await session.execute(
        select(Kitchen).where(Kitchen.id == kitchen_id, Kitchen.owner_id == owner.id)
    )
    kitchen = result.scalar_one_or_none()
    if not kitchen:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kitchen not found")
    try:
        kitchen = await update_kitchen_delivery_settings(session, kitchen, body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await session.commit()
    return await kitchen_to_response(session, kitchen)


@router.get("/kitchens/public/nearby", response_model=KitchenNearbyListResponse)
async def kitchens_public_nearby(
    session: Annotated[AsyncSession, Depends(get_db)],
    latitude: float = Query(..., ge=-90, le=90, description="Customer latitude"),
    longitude: float = Query(..., ge=-180, le=180, description="Customer longitude"),
    limit: int = Query(20, ge=1, le=100),
    max_km: float = Query(50.0, gt=0, le=200, description="Search radius in km"),
    sort: str = Query("asc", pattern="^(asc|desc)$", description="asc = nearest first"),
    diet: str | None = Query(None, pattern="^(veg|non_veg|vegan)$"),
    live_capture: bool | None = Query(None, description="Only kitchens with live-capture hero dishes"),
) -> KitchenNearbyListResponse:
    """List active cloud kitchens near a point, sorted by distance."""
    kitchens = await list_kitchens_nearby(
        session,
        latitude=latitude,
        longitude=longitude,
        limit=limit,
        max_km=max_km,
        sort=sort,
        diet=diet,
        live_capture=live_capture,
    )
    return KitchenNearbyListResponse(
        kitchens=kitchens,
        total=len(kitchens),
        customer_latitude=latitude,
        customer_longitude=longitude,
        sort=sort,
    )


@router.get("/kitchens/public/by-code/{code}", response_model=KitchenPublicResponse)
async def kitchen_public_by_code(
    code: str,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> KitchenPublicResponse:
    """Public kitchen lookup for customers (by kitchen code e.g. CKPNQ001)."""
    result = await session.execute(
        select(Kitchen).where(Kitchen.code == code.strip().upper())
    )
    kitchen = result.scalar_one_or_none()
    if not kitchen or kitchen.status != "active":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kitchen not found")
    return KitchenPublicResponse(
        id=kitchen.id,
        code=kitchen.code,
        name=kitchen.name,
        city=kitchen.city,
        state=kitchen.state,
        status=kitchen.status,
    )
