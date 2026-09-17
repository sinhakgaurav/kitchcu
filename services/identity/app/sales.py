"""Sales field onboarding + owner training playbook (P55)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Kitchen, KitchenTrainingProgress, Owner, PlatformAdmin
from app.schemas import (
    KitchenCreateRequest,
    OwnerRegisterRequest,
    create_kitchen,
    normalize_india_phone,
    normalize_optional_email,
    normalize_person_name,
    register_owner,
)
from ckac_common.admin_rbac import assert_admin_permission, load_permissions_for_role, role_has_permission
from ckac_common.auth import stream_key
from ckac_common.event_bus import EventPublisher
from ckac_common.platform_config import require_feature

SALES_FEATURE = "sales_onboarding"

# How a field rep walks an owner through the Kitchen app — not a CMS.
TRAINING_STEPS: list[dict[str, str]] = [
    {
        "key": "profile",
        "title": "Kitchen profile is true",
        "coach": "Open Kitchen app → Setup. Confirm name, street, and the map pin match the stall. Code never changes.",
    },
    {
        "key": "live_hero",
        "title": "Live-capture a dish hero",
        "coach": "Add Dish → camera only. No gallery stock photos. Publish when the plate in the photo is the plate they sell.",
    },
    {
        "key": "recipe",
        "title": "Map the first recipe",
        "coach": "Ingredients → pantry SKU → dish recipe quantities. This drives stock, health, and calories.",
    },
    {
        "key": "radius",
        "title": "Set delivery radius",
        "coach": "Setup → delivery. Free radius and max km must match how far they actually ride.",
    },
    {
        "key": "kyc",
        "title": "Owner KYC photos",
        "coach": "Owner profile: live photo + Aadhaar + PAN. Support uses this when a diner disputes identity.",
    },
    {
        "key": "test_order",
        "title": "Place a test order",
        "coach": "New Order on Kitchen (or diner Customer app). Walk received → accepted → ready so they trust the board.",
    },
    {
        "key": "whatsapp",
        "title": "WhatsApp number check",
        "coach": "If they take WhatsApp orders, confirm the kitchen phone_number_id with Super Admin — sales never pastes Meta app secrets.",
    },
    {
        "key": "handoff",
        "title": "Owner can login alone",
        "coach": "They request OTP on kitchen.kitchcu.com (or Kitchen app) with their phone. Demo OTP is 123456 only in local/demo.",
    },
]


class SalesOnboardRequest(BaseModel):
    owner_name: str = Field(..., min_length=2, max_length=255)
    owner_phone: str = Field(..., min_length=10, max_length=16)
    owner_email: EmailStr | None = None
    kitchen_name: str = Field(..., min_length=2, max_length=255)
    description: str | None = None
    address_line: str = Field(..., min_length=3, max_length=255)
    city: str = Field(..., min_length=2, max_length=80)
    state: str = Field(..., min_length=2, max_length=80)
    pincode: str | None = Field(default=None, max_length=12)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)

    @field_validator("owner_phone")
    @classmethod
    def _phone(cls, v: str) -> str:
        return normalize_india_phone(v)

    @field_validator("owner_name", "kitchen_name")
    @classmethod
    def _name(cls, v: str) -> str:
        return normalize_person_name(v)

    @field_validator("owner_email")
    @classmethod
    def _email(cls, v: EmailStr | None) -> str | None:
        return normalize_optional_email(v)


class TrainingStepState(BaseModel):
    key: str
    title: str
    coach: str
    completed: bool
    completed_at: datetime | None = None
    note: str | None = None


class KitchenTrainingResponse(BaseModel):
    kitchen_id: uuid.UUID
    completed: int
    total: int
    steps: list[TrainingStepState]


class TrainingStepUpdate(BaseModel):
    step_key: str = Field(..., min_length=2, max_length=64)
    completed: bool = True
    note: str | None = Field(default=None, max_length=500)


class SalesKitchenCard(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    city: str | None
    status: str
    owner_name: str
    owner_phone: str
    owner_id: uuid.UUID
    onboarded_by_admin_id: uuid.UUID | None = None
    training_completed: int = 0
    training_total: int = Field(default_factory=lambda: len(TRAINING_STEPS))


class SalesOnboardResponse(BaseModel):
    owner_created: bool
    kitchen: SalesKitchenCard
    training: KitchenTrainingResponse
    owner_login_hint: str = (
        "Owner signs in on the Kitchen app with this phone and OTP. "
        "Local/demo OTP is 123456 — production sends WhatsApp OTP."
    )


def is_sales_role(admin: PlatformAdmin) -> bool:
    return admin.role == "sales"


async def assert_sales_feature(session: AsyncSession) -> None:
    try:
        await require_feature(session, SALES_FEATURE)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


async def assert_kitchen_visible(
    session: AsyncSession,
    admin: PlatformAdmin,
    kitchen: Kitchen,
) -> None:
    grants = await load_permissions_for_role(session, admin.role)
    if "*" in grants:
        return
    if is_sales_role(admin):
        if kitchen.onboarded_by_admin_id != admin.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Kitchen is not in your book")
        return
    await assert_admin_permission(session, role=admin.role, permission="kitchens:read")


async def assert_kitchen_trainable(
    session: AsyncSession,
    admin: PlatformAdmin,
    kitchen: Kitchen,
) -> None:
    grants = await load_permissions_for_role(session, admin.role)
    if "*" in grants:
        return
    if is_sales_role(admin):
        await assert_admin_permission(session, role=admin.role, permission="sales:write")
        if kitchen.onboarded_by_admin_id != admin.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Kitchen is not in your book")
        return
    if role_has_permission(grants, "kitchens:write") or role_has_permission(grants, "sales:write"):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing permission: sales:write")


def _step_catalog() -> dict[str, dict[str, str]]:
    return {s["key"]: s for s in TRAINING_STEPS}


async def training_completed_map(
    session: AsyncSession, kitchen_ids: list[uuid.UUID]
) -> dict[uuid.UUID, int]:
    if not kitchen_ids:
        return {}
    rows = (
        await session.execute(
            select(KitchenTrainingProgress.kitchen_id, func.count())
            .where(KitchenTrainingProgress.kitchen_id.in_(kitchen_ids))
            .group_by(KitchenTrainingProgress.kitchen_id)
        )
    ).all()
    return {kid: int(n) for kid, n in rows}


async def training_response(session: AsyncSession, kitchen_id: uuid.UUID) -> KitchenTrainingResponse:
    rows = list(
        (
            await session.execute(
                select(KitchenTrainingProgress).where(KitchenTrainingProgress.kitchen_id == kitchen_id)
            )
        )
        .scalars()
        .all()
    )
    by_key = {r.step_key: r for r in rows}
    steps: list[TrainingStepState] = []
    done = 0
    for spec in TRAINING_STEPS:
        row = by_key.get(spec["key"])
        completed = row is not None
        if completed:
            done += 1
        steps.append(
            TrainingStepState(
                key=spec["key"],
                title=spec["title"],
                coach=spec["coach"],
                completed=completed,
                completed_at=row.completed_at if row else None,
                note=row.note if row else None,
            )
        )
    return KitchenTrainingResponse(
        kitchen_id=kitchen_id,
        completed=done,
        total=len(TRAINING_STEPS),
        steps=steps,
    )


def kitchen_card(
    kitchen: Kitchen,
    owner: Owner,
    *,
    training_completed: int = 0,
) -> SalesKitchenCard:
    return SalesKitchenCard(
        id=kitchen.id,
        code=kitchen.code,
        name=kitchen.name,
        city=kitchen.city,
        status=kitchen.status,
        owner_name=owner.name,
        owner_phone=owner.phone,
        owner_id=owner.id,
        onboarded_by_admin_id=kitchen.onboarded_by_admin_id,
        training_completed=training_completed,
        training_total=len(TRAINING_STEPS),
    )


async def onboard_kitchen(
    session: AsyncSession,
    admin: PlatformAdmin,
    body: SalesOnboardRequest,
    publisher: EventPublisher,
) -> SalesOnboardResponse:
    await assert_sales_feature(session)
    await assert_admin_permission(session, role=admin.role, permission="sales:write")

    existing = (
        await session.execute(select(Owner).where(Owner.phone == body.owner_phone))
    ).scalar_one_or_none()
    owner_created = existing is None
    if existing:
        owner = existing
    else:
        owner = await register_owner(
            session,
            OwnerRegisterRequest(
                phone=body.owner_phone,
                name=body.owner_name,
                email=body.owner_email,
            ),
        )
        event = EventPublisher.build(
            event_type="owner.created",
            aggregate_type="owner",
            aggregate_id=str(owner.id),
            producer="identity-service",
            payload={
                "owner_id": str(owner.id),
                "source": "sales_onboard",
                "onboarded_by": str(admin.id),
            },
        )
        await publisher.publish(stream_key("identity", "owner"), event, session=session)

    kitchen = await create_kitchen(
        session,
        owner.id,
        KitchenCreateRequest(
            name=body.kitchen_name,
            description=body.description,
            address_line=body.address_line,
            city=body.city,
            state=body.state,
            pincode=body.pincode,
            latitude=body.latitude,
            longitude=body.longitude,
        ),
        onboarded_by_admin_id=admin.id,
    )
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
            "onboarded_by": str(admin.id),
            "source": "sales_onboard",
        },
    )
    await publisher.publish(stream_key("identity", "kitchen"), event, session=session)
    training = await training_response(session, kitchen.id)
    return SalesOnboardResponse(
        owner_created=owner_created,
        kitchen=kitchen_card(kitchen, owner, training_completed=training.completed),
        training=training,
    )


async def set_training_step(
    session: AsyncSession,
    admin: PlatformAdmin,
    kitchen: Kitchen,
    body: TrainingStepUpdate,
    publisher: EventPublisher,
) -> KitchenTrainingResponse:
    catalog = _step_catalog()
    if body.step_key not in catalog:
        raise HTTPException(status_code=400, detail="Unknown training step")
    await assert_kitchen_trainable(session, admin, kitchen)
    row = await session.get(KitchenTrainingProgress, (kitchen.id, body.step_key))
    if body.completed:
        if row is None:
            session.add(
                KitchenTrainingProgress(
                    kitchen_id=kitchen.id,
                    step_key=body.step_key,
                    completed_at=datetime.now(UTC),
                    completed_by=admin.id,
                    note=body.note,
                )
            )
        else:
            row.completed_at = datetime.now(UTC)
            row.completed_by = admin.id
            if body.note is not None:
                row.note = body.note
    elif row is not None:
        await session.delete(row)
    await session.flush()
    event = EventPublisher.build(
        event_type="kitchen.training.updated",
        aggregate_type="kitchen",
        aggregate_id=str(kitchen.id),
        producer="identity-service",
        payload={
            "kitchen_id": str(kitchen.id),
            "step_key": body.step_key,
            "completed": body.completed,
            "actor_id": str(admin.id),
        },
    )
    await publisher.publish(stream_key("identity", "kitchen"), event, session=session)
    return await training_response(session, kitchen.id)


def apply_sales_kitchen_filter(query: Any, admin: PlatformAdmin) -> Any:
    if is_sales_role(admin):
        return query.where(Kitchen.onboarded_by_admin_id == admin.id)
    return query
