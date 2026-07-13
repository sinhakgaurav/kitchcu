"""Platform admin API — full control over owners, kitchens, orders."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Kitchen, Owner, PlatformAdmin
from ckac_common.config import get_settings
from ckac_common.database import get_db

router = APIRouter(prefix="/admin", tags=["admin"])
security = HTTPBearer(auto_error=False)
settings = get_settings()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode()[:72], password_hash.encode())
    except ValueError:
        return False


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)


class AdminTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class AdminProfile(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    role: str

    model_config = {"from_attributes": True}


class PlatformStats(BaseModel):
    owners: int
    kitchens: int
    active_kitchens: int
    orders: int
    dishes: int


class AdminOwnerRow(BaseModel):
    id: uuid.UUID
    name: str
    phone: str
    email: str | None
    subscription_tier: str
    subscription_status: str
    kitchen_count: int


class AdminKitchenRow(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    city: str | None
    status: str
    owner_name: str
    owner_phone: str


class AdminOrderRow(BaseModel):
    id: uuid.UUID
    order_code: str
    kitchen_id: uuid.UUID
    kitchen_name: str
    status: str
    total: float
    customer_name: str | None
    created_at: datetime


class KitchenStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(active|suspended|pending_verification)$")


def create_admin_token(admin_id: uuid.UUID, email: str) -> AdminTokenResponse:
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_access_expire_minutes)
    payload = {"sub": str(admin_id), "email": email, "type": "admin", "exp": expire}
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return AdminTokenResponse(
        access_token=token,
        expires_in=settings.jwt_access_expire_minutes * 60,
    )


async def get_current_admin(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PlatformAdmin:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(
            credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        if payload.get("type") != "admin":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        admin_id = uuid.UUID(payload["sub"])
    except (JWTError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    result = await session.execute(
        select(PlatformAdmin).where(PlatformAdmin.id == admin_id, PlatformAdmin.is_active.is_(True))
    )
    admin = result.scalar_one_or_none()
    if not admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin not found")
    return admin


async def ensure_default_admin(session: AsyncSession) -> None:
    email = settings.admin_email.lower()
    result = await session.execute(select(PlatformAdmin).where(PlatformAdmin.email == email))
    if result.scalar_one_or_none():
        return
    session.add(
        PlatformAdmin(
            email=email,
            password_hash=hash_password(settings.admin_password),
            name="kitchCU Platform Admin",
            role="superadmin",
        )
    )
    await session.flush()


@router.post("/auth/login", response_model=AdminTokenResponse)
async def admin_login(body: AdminLoginRequest, session: Annotated[AsyncSession, Depends(get_db)]) -> AdminTokenResponse:
    await ensure_default_admin(session)
    await session.commit()
    result = await session.execute(
        select(PlatformAdmin).where(
            PlatformAdmin.email == body.email.lower(),
            PlatformAdmin.is_active.is_(True),
        )
    )
    admin = result.scalar_one_or_none()
    if not admin or not verify_password(body.password, admin.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return create_admin_token(admin.id, admin.email)


@router.get("/me", response_model=AdminProfile)
async def admin_me(admin: Annotated[PlatformAdmin, Depends(get_current_admin)]) -> AdminProfile:
    return AdminProfile.model_validate(admin)


@router.get("/stats", response_model=PlatformStats)
async def admin_stats(
    admin: Annotated[PlatformAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> PlatformStats:
    _ = admin
    owners = (await session.execute(select(func.count()).select_from(Owner))).scalar_one()
    kitchens = (await session.execute(select(func.count()).select_from(Kitchen))).scalar_one()
    active = (
        await session.execute(select(func.count()).select_from(Kitchen).where(Kitchen.status == "active"))
    ).scalar_one()
    orders = (
        await session.execute(text("SELECT COUNT(*) FROM ckac_orders.orders"))
    ).scalar_one()
    dishes = (
        await session.execute(text("SELECT COUNT(*) FROM ckac_catalog.dishes WHERE is_active = true"))
    ).scalar_one()
    return PlatformStats(
        owners=owners,
        kitchens=kitchens,
        active_kitchens=active,
        orders=orders,
        dishes=dishes,
    )


@router.get("/owners", response_model=list[AdminOwnerRow])
async def admin_owners(
    admin: Annotated[PlatformAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[AdminOwnerRow]:
    _ = admin
    result = await session.execute(select(Owner).order_by(Owner.created_at.desc()).limit(200))
    owners = list(result.scalars().all())
    rows: list[AdminOwnerRow] = []
    for o in owners:
        kc = (
            await session.execute(select(func.count()).select_from(Kitchen).where(Kitchen.owner_id == o.id))
        ).scalar_one()
        rows.append(
            AdminOwnerRow(
                id=o.id,
                name=o.name,
                phone=o.phone,
                email=o.email,
                subscription_tier=o.subscription_tier,
                subscription_status=o.subscription_status,
                kitchen_count=kc,
            )
        )
    return rows


@router.get("/kitchens", response_model=list[AdminKitchenRow])
async def admin_kitchens(
    admin: Annotated[PlatformAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[AdminKitchenRow]:
    _ = admin
    result = await session.execute(
        select(Kitchen, Owner)
        .join(Owner, Owner.id == Kitchen.owner_id)
        .order_by(Kitchen.created_at.desc())
        .limit(300)
    )
    return [
        AdminKitchenRow(
            id=k.id,
            code=k.code,
            name=k.name,
            city=k.city,
            status=k.status,
            owner_name=o.name,
            owner_phone=o.phone,
        )
        for k, o in result.all()
    ]


@router.patch("/kitchens/{kitchen_id}/status", response_model=AdminKitchenRow)
async def admin_kitchen_status(
    kitchen_id: uuid.UUID,
    body: KitchenStatusUpdate,
    admin: Annotated[PlatformAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AdminKitchenRow:
    _ = admin
    result = await session.execute(
        select(Kitchen, Owner)
        .join(Owner, Owner.id == Kitchen.owner_id)
        .where(Kitchen.id == kitchen_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Kitchen not found")
    kitchen, owner = row
    kitchen.status = body.status
    await session.commit()
    return AdminKitchenRow(
        id=kitchen.id,
        code=kitchen.code,
        name=kitchen.name,
        city=kitchen.city,
        status=kitchen.status,
        owner_name=owner.name,
        owner_phone=owner.phone,
    )


@router.get("/orders", response_model=list[AdminOrderRow])
async def admin_orders(
    admin: Annotated[PlatformAdmin, Depends(get_current_admin)],
    session: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 100,
) -> list[AdminOrderRow]:
    _ = admin
    result = await session.execute(
        text(
            """
            SELECT o.id, o.order_code, o.kitchen_id, o.status, o.total, o.customer_name, o.created_at,
                   k.name AS kitchen_name
            FROM ckac_orders.orders o
            JOIN ckac_identity.kitchens k ON k.id = o.kitchen_id
            ORDER BY o.created_at DESC
            LIMIT :lim
            """
        ),
        {"lim": min(limit, 500)},
    )
    return [
        AdminOrderRow(
            id=r.id,
            order_code=r.order_code,
            kitchen_id=r.kitchen_id,
            kitchen_name=r.kitchen_name,
            status=r.status,
            total=float(r.total),
            customer_name=r.customer_name,
            created_at=r.created_at,
        )
        for r in result.mappings().all()
    ]
