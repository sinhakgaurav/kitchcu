import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Kitchen, Owner
from app.discovery import DiscoveryHomeResponse, build_discovery_home
from app.schemas import (
    KitchenCreateRequest,
    KitchenDeliverySettingsUpdate,
    KitchenNearbyListResponse,
    KitchenBrandedPageUpdate,
    KitchenPublicResponse,
    KitchenResponse,
    KitchenWhatsAppIntegrationResponse,
    KitchenWhatsAppIntegrationUpdate,
    OTPRequest,
    OTPVerifyRequest,
    OwnerRegisterRequest,
    OwnerResponse,
    TokenResponse,
    create_access_token,
    create_kitchen,
    get_kitchen_whatsapp_integration,
    kitchen_to_public_response,
    kitchen_to_response,
    list_kitchens_nearby,
    register_owner,
    update_kitchen_branded_page,
    update_kitchen_delivery_settings,
    update_kitchen_whatsapp_integration,
)
from ckac_common.auth import stream_key
from ckac_common.config import get_settings
from ckac_common.database import get_db
from ckac_common.event_bus import EventPublisher
from ckac_common.openapi import RESP_400, RESP_401, RESP_404, RESP_409, RESP_422, auth_errors
from ckac_common.platform_config import allows_fixed_dev_otp, get_demo_otp, require_feature

router = APIRouter()
security = HTTPBearer(auto_error=False)
settings = get_settings()

_DEV_OTP: dict[str, str] = {}
_OWNER_OTP_PREFIX = "otp:owner:"
_OWNER_OTP_TTL = 600


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


@router.post(
    "/auth/otp/request",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request owner login OTP",
    description=(
        "Sends a one-time password to the owner's phone via WhatsApp/SMS to start login.\n\n"
        "**Body:** phone (10-digit India mobile or E.164).\n\n"
        "**Response 202:** confirmation message. In `development`/`test` the OTP is "
        "`DEMO_OTP` (default `123456`) via `dev_hint`. Outside that, returns 503 until "
        "WhatsApp outbound delivery is configured.\n\n"
        "Follow up with `POST /auth/otp/verify` to exchange the OTP for a JWT."
    ),
    responses={422: RESP_422},
    tags=["Auth"],
)
async def request_otp(body: OTPRequest) -> dict[str, str]:
    phone = body.phone.strip()
    if allows_fixed_dev_otp():
        otp = get_demo_otp()
        _DEV_OTP[phone] = otp
        return {"message": "OTP sent", "dev_hint": f"Use {otp} in development"}

    from app.main import redis_client
    from app.otp_delivery import (
        OWNER_OTP_PREFIX,
        generate_otp_code,
        send_otp_whatsapp,
        store_otp_redis,
    )

    code = generate_otp_code()
    try:
        await store_otp_redis(redis_client, prefix=OWNER_OTP_PREFIX, phone=phone, code=code)
        await send_otp_whatsapp(phone=phone, code=code, purpose="owner_login")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "OTP delivery unavailable. Configure WHATSAPP_ACCESS_TOKEN + "
                "WHATSAPP_OTP_PHONE_NUMBER_ID (or Admin → API Keys) and ensure Redis is up."
            ),
        ) from exc
    return {"message": "OTP sent via WhatsApp"}


@router.post(
    "/auth/otp/verify",
    response_model=TokenResponse,
    summary="Verify owner OTP and issue JWT",
    description=(
        "Exchanges a one-time password for an owner Bearer JWT.\n\n"
        "**Body:** phone + otp (dev/test OTP is `DEMO_OTP` / `123456`).\n\n"
        "**Response 200:** access_token (JWT type=owner), token_type=bearer, expires_in seconds.\n\n"
        "Use `Authorization: Bearer <access_token>` on subsequent owner APIs."
    ),
    responses={401: RESP_401, 404: RESP_404, 422: RESP_422},
    tags=["Auth"],
)
async def verify_otp(
    body: OTPVerifyRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    phone = body.phone.strip()
    if allows_fixed_dev_otp():
        expected = _DEV_OTP.get(phone)
    else:
        from app.main import redis_client
        from app.otp_delivery import OWNER_OTP_PREFIX

        key = f"{OWNER_OTP_PREFIX}{phone}"
        expected = await redis_client.get(key) if redis_client else None
        if expected and expected == body.otp and redis_client:
            await redis_client.delete(key)
    if not expected or expected != body.otp:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid OTP")

    result = await session.execute(select(Owner).where(Owner.phone == phone))
    owner = result.scalar_one_or_none()
    if not owner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Owner not registered")
    return create_access_token(owner.id, owner.phone)


@router.post(
    "/owners/register",
    response_model=OwnerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new owner",
    description=(
        "Creates a kitchCU owner account. No auth required — this is the entry point before "
        "the owner ever has a JWT.\n\n"
        "**Body:** phone (unique login identifier), name, optional email.\n\n"
        "**Response 201:** the created owner profile, starting on the `trial` subscription tier. "
        "Follow up with `POST /auth/otp/request` + `/auth/otp/verify` to log in, then "
        "`POST /kitchens` to onboard a kitchen."
    ),
    responses={409: RESP_409, 422: RESP_422},
    tags=["Owners"],
)
async def owner_register(
    body: OwnerRegisterRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Owner:
    try:
        await require_feature(session, "owner_registrations")
        owner = await register_owner(session, body)
    except ValueError as exc:
        detail = str(exc)
        if detail.startswith("Feature '") and detail.endswith("' is disabled"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail) from exc
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from exc
    return owner


@router.get(
    "/owners/me",
    response_model=OwnerResponse,
    summary="Get the authenticated owner's profile",
    description=(
        "Returns the profile of the owner identified by the Bearer JWT.\n\n"
        "**Auth:** owner JWT (`Authorization: Bearer <access_token>`) required.\n\n"
        "**Response 200:** owner profile including subscription tier/status."
    ),
    responses=auth_errors(),
    tags=["Owners"],
)
async def owner_me(owner: Annotated[Owner, Depends(get_current_owner)]) -> Owner:
    return owner


@router.post(
    "/kitchens",
    response_model=KitchenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Onboard a new kitchen",
    description=(
        "Creates a cloud kitchen owned by the authenticated owner and assigns a unique "
        "kitchen code (`CK` + city(3) + seq(3), e.g. `CKPNQ001`).\n\n"
        "**Auth:** owner JWT required.\n\n"
        "**Body:** name, address/city/state/pincode, lat/lng, and delivery radius/fee settings.\n\n"
        "**Response 201:** the created kitchen with generated `code`. Publishes a "
        "`kitchen.created` event on `ckac:identity:kitchen`."
    ),
    responses=auth_errors(),
    tags=["Kitchens"],
)
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
    from app.referral import try_reward_kitchen_onboard

    await try_reward_kitchen_onboard(
        session, kitchen=kitchen, owner=owner, publisher=publisher
    )
    return await kitchen_to_response(session, kitchen)


@router.get(
    "/kitchens/me",
    response_model=list[KitchenResponse],
    summary="List kitchens owned by the authenticated owner",
    description=(
        "Returns every kitchen belonging to the authenticated owner (an owner may run "
        "multiple kitchens).\n\n"
        "**Auth:** owner JWT required.\n\n"
        "**Response 200:** array of kitchen records; empty array if the owner has none yet."
    ),
    responses=auth_errors(),
    tags=["Kitchens"],
)
async def kitchens_me(
    owner: Annotated[Owner, Depends(get_current_owner)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[KitchenResponse]:
    result = await session.execute(select(Kitchen).where(Kitchen.owner_id == owner.id))
    kitchens = result.scalars().all()
    return [await kitchen_to_response(session, k) for k in kitchens]


@router.patch(
    "/kitchens/{kitchen_id}/delivery-settings",
    response_model=KitchenResponse,
    summary="Update a kitchen's delivery fee/radius settings",
    description=(
        "Partially updates delivery radius, per-km fee, flat fee, free-delivery threshold, "
        "and tracking notification interval for a kitchen owned by the authenticated owner. "
        "All body fields are optional — only provided fields are changed.\n\n"
        "**Auth:** owner JWT required; the kitchen must belong to the caller.\n\n"
        "**Response 200:** the updated kitchen record.\n\n"
        "**400:** `free_delivery_radius_km` would exceed `max_delivery_radius_km`.\n\n"
        "**404:** kitchen does not exist or is not owned by the caller."
    ),
    responses={**auth_errors(include_404=True), 400: RESP_400},
    tags=["Kitchens"],
)
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


@router.patch(
    "/kitchens/{kitchen_id}/branded-page",
    response_model=KitchenResponse,
    summary="Publish / customize the kitchen branded storefront",
    description=(
        "Owner-only — enable a kitchen-first public page at `customer…/k/{code}` for menu showcase, "
        "checkout, and bill download, with a **Powered by kitchCU** footer. Settings live in "
        "`kitchens.settings.branded_page` (no schema migration). Publishes `kitchen.branded_page.updated`."
    ),
    responses={**auth_errors(include_404=True), 400: RESP_400, 422: RESP_422},
    tags=["Kitchens"],
)
async def kitchen_branded_page_update(
    kitchen_id: uuid.UUID,
    body: KitchenBrandedPageUpdate,
    owner: Annotated[Owner, Depends(get_current_owner)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> KitchenResponse:
    result = await session.execute(
        select(Kitchen).where(Kitchen.id == kitchen_id, Kitchen.owner_id == owner.id)
    )
    kitchen = result.scalar_one_or_none()
    if not kitchen:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kitchen not found")
    try:
        kitchen = await update_kitchen_branded_page(session, kitchen, body, publisher)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await session.commit()
    return await kitchen_to_response(session, kitchen)


@router.get(
    "/kitchens/{kitchen_id}/whatsapp-integration",
    response_model=KitchenWhatsAppIntegrationResponse,
    summary="Get kitchen WhatsApp Business linkage (F01)",
    description=(
        "Owner-only — Meta Cloud API phone_number_id used to route inbound WhatsApp orders. "
        "Platform App Secret / Verify Token stay in Super Admin API Keys."
    ),
    responses=auth_errors(include_404=True),
    tags=["Kitchens"],
)
async def kitchen_whatsapp_get(
    kitchen_id: uuid.UUID,
    owner: Annotated[Owner, Depends(get_current_owner)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> KitchenWhatsAppIntegrationResponse:
    result = await session.execute(
        select(Kitchen).where(Kitchen.id == kitchen_id, Kitchen.owner_id == owner.id)
    )
    kitchen = result.scalar_one_or_none()
    if not kitchen:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kitchen not found")
    return await get_kitchen_whatsapp_integration(session, kitchen)


@router.put(
    "/kitchens/{kitchen_id}/whatsapp-integration",
    response_model=KitchenWhatsAppIntegrationResponse,
    summary="Connect or disconnect WhatsApp Business for a kitchen",
    description=(
        "Owner-only — set Meta phone_number_id (unique per kitchen) and optional display E.164. "
        "Publishes `kitchen.whatsapp.updated`. Respects per-kitchen `whatsapp` module kill-switch."
    ),
    responses={**auth_errors(include_404=True), 400: RESP_400},
    tags=["Kitchens"],
)
async def kitchen_whatsapp_put(
    kitchen_id: uuid.UUID,
    body: KitchenWhatsAppIntegrationUpdate,
    owner: Annotated[Owner, Depends(get_current_owner)],
    session: Annotated[AsyncSession, Depends(get_db)],
    publisher: Annotated[EventPublisher, Depends(get_publisher)],
) -> KitchenWhatsAppIntegrationResponse:
    result = await session.execute(
        select(Kitchen).where(Kitchen.id == kitchen_id, Kitchen.owner_id == owner.id)
    )
    kitchen = result.scalar_one_or_none()
    if not kitchen:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kitchen not found")
    try:
        from ckac_common.platform_config import feature_http_status

        out = await update_kitchen_whatsapp_integration(session, kitchen, body, publisher)
    except ValueError as exc:
        code = feature_http_status(exc) or status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    await session.commit()
    return out


@router.get(
    "/discovery/home",
    response_model=DiscoveryHomeResponse,
    summary="Customer discovery home feed",
    description=(
        "Public geo-scoped order pathways for the customer app: near you, featured, "
        "most liked, live now, and cheapest dishes in range. Single round-trip — "
        "no client N+1 across menus/ratings."
    ),
    responses={422: RESP_422},
    tags=["Discovery"],
)
async def discovery_home(
    session: Annotated[AsyncSession, Depends(get_db)],
    latitude: float = Query(..., ge=-90, le=90, examples=[18.5204]),
    longitude: float = Query(..., ge=-180, le=180, examples=[73.8567]),
    max_km: float = Query(25.0, gt=0, le=200, examples=[25.0]),
    section_limit: int = Query(12, ge=1, le=30, examples=[12]),
) -> DiscoveryHomeResponse:
    return await build_discovery_home(
        session,
        latitude=latitude,
        longitude=longitude,
        max_km=max_km,
        section_limit=section_limit,
    )


@router.get(
    "/kitchens/public/nearby",
    response_model=KitchenNearbyListResponse,
    summary="Discover active kitchens near a location",
    description=(
        "Public, unauthenticated discovery endpoint used by the customer app. Lists active "
        "cloud kitchens within `max_km` of the given point, sorted by distance, with optional "
        "diet/live-capture/live-streaming filters.\n\n"
        "**Auth:** none — public endpoint.\n\n"
        "**Response 200:** distance-sorted kitchen list with per-kitchen discovery signals "
        "(`has_veg`, `has_non_veg`, `has_live_capture`, `is_live_now`)."
    ),
    responses={422: RESP_422},
    tags=["Discovery"],
)
async def kitchens_public_nearby(
    session: Annotated[AsyncSession, Depends(get_db)],
    latitude: float = Query(..., ge=-90, le=90, description="Customer latitude", examples=[18.5204]),
    longitude: float = Query(..., ge=-180, le=180, description="Customer longitude", examples=[73.8567]),
    limit: int = Query(20, ge=1, le=100, description="Max kitchens to return.", examples=[20]),
    max_km: float = Query(50.0, gt=0, le=200, description="Search radius in km", examples=[50.0]),
    sort: str = Query("asc", pattern="^(asc|desc)$", description="asc = nearest first", examples=["asc"]),
    diet: str | None = Query(None, pattern="^(veg|non_veg|vegan)$", description="Filter to kitchens with an active dish in this diet category."),
    live_capture: bool | None = Query(None, description="Only kitchens with live-capture hero dishes"),
    live_only: bool | None = Query(None, description="Only kitchens currently streaming live prep"),
) -> KitchenNearbyListResponse:
    kitchens = await list_kitchens_nearby(
        session,
        latitude=latitude,
        longitude=longitude,
        limit=limit,
        max_km=max_km,
        sort=sort,
        diet=diet,
        live_capture=live_capture,
        live_only=live_only,
    )
    return KitchenNearbyListResponse(
        kitchens=kitchens,
        total=len(kitchens),
        customer_latitude=latitude,
        customer_longitude=longitude,
        sort=sort,
    )


@router.get(
    "/kitchens/public/by-code/{code}",
    response_model=KitchenPublicResponse,
    summary="Look up a public kitchen by its code",
    description=(
        "Public, unauthenticated lookup of a single active kitchen by its unique code "
        "(e.g. `CKPNQ001`) — used for deep links and QR codes.\n\n"
        "**Auth:** none — public endpoint.\n\n"
        "**Response 200:** minimal public kitchen record.\n\n"
        "**404:** no active kitchen with that code."
    ),
    responses={404: RESP_404},
    tags=["Discovery"],
)
async def kitchen_public_by_code(
    code: str,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> KitchenPublicResponse:
    result = await session.execute(
        select(Kitchen).where(Kitchen.code == code.strip().upper())
    )
    kitchen = result.scalar_one_or_none()
    if not kitchen or kitchen.status != "active":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kitchen not found")
    return kitchen_to_public_response(kitchen)
