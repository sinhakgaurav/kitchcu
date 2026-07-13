"""Learning portal domain — curated recipes (F21) and dish trials (F22)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog_client import activate_dish, create_trial_dish
from app.models import CuratedRecipe, DishTrial, TrialInvite, TrialRating
from app.notify_client import notify_trial_sample_blast
from ckac_common.auth import stream_key
from ckac_common.event_bus import EventPublisher

MIN_INVITES = 5
MAX_INVITES = 20
DEFAULT_RATING_THRESHOLD = 4.0


class CuratedRecipeResponse(BaseModel):
    id: uuid.UUID
    title: str
    slug: str
    category: str
    cuisine: str
    description: str
    ingredients: list
    prep_steps: list
    image_url: str
    source_name: str
    source_url: str | None

    model_config = {"from_attributes": True}


class CuratedRecipeListResponse(BaseModel):
    recipes: list[CuratedRecipeResponse]
    total: int


class LearnRecipeRequest(BaseModel):
    recipe_id: uuid.UUID
    dish_name: str | None = Field(default=None, max_length=255)
    price: float = Field(default=99.0, gt=0)
    cuisine_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    prep_time_min: int = Field(default=30, gt=0)


class TrialInviteResponse(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    customer_name: str | None
    customer_phone_masked: str
    status: str
    home_taste_score: int | None = None
    quality_score: int | None = None

    model_config = {"from_attributes": True}


class DishTrialResponse(BaseModel):
    id: uuid.UUID
    kitchen_id: uuid.UUID
    curated_recipe_id: uuid.UUID | None
    catalog_dish_id: uuid.UUID
    dish_name: str
    status: str
    promo_type: str
    sample_price: float | None
    rating_threshold: float
    avg_rating: float | None
    invite_count: int
    whatsapp_sent_at: datetime | None
    promoted_at: datetime | None
    created_at: datetime
    invites: list[TrialInviteResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class DishTrialListResponse(BaseModel):
    trials: list[DishTrialResponse]
    total: int


class TrialInvitesRequest(BaseModel):
    customer_ids: list[uuid.UUID] = Field(min_length=MIN_INVITES, max_length=MAX_INVITES)
    promo_type: Literal["free", "paid_sample"] = "free"
    sample_price: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def paid_requires_price(self) -> TrialInvitesRequest:
        if self.promo_type == "paid_sample" and not self.sample_price:
            raise ValueError("sample_price required for paid_sample promos")
        return self


class TrialRatingRequest(BaseModel):
    invite_id: uuid.UUID
    home_taste_score: int = Field(ge=1, le=5)
    quality_score: int = Field(ge=1, le=5)
    feedback: str | None = Field(default=None, max_length=2000)


def _mask_phone(phone: str) -> str:
    if len(phone) < 6:
        return "***"
    return f"{phone[:4]}***{phone[-2:]}"


def _overall(home: int, quality: int) -> float:
    return round(0.6 * home + 0.4 * quality, 2)


async def list_curated_recipes(
    session: AsyncSession,
    *,
    category: str | None = None,
    limit: int = 50,
) -> CuratedRecipeListResponse:
    q = select(CuratedRecipe).where(CuratedRecipe.is_active.is_(True))
    if category:
        q = q.where(CuratedRecipe.category == category)
    q = q.order_by(CuratedRecipe.title).limit(limit)
    rows = list((await session.execute(q)).scalars().all())
    return CuratedRecipeListResponse(
        recipes=[CuratedRecipeResponse.model_validate(r) for r in rows],
        total=len(rows),
    )


async def get_curated_recipe(session: AsyncSession, recipe_id: uuid.UUID) -> CuratedRecipe:
    row = (
        await session.execute(
            select(CuratedRecipe).where(CuratedRecipe.id == recipe_id, CuratedRecipe.is_active.is_(True))
        )
    ).scalar_one_or_none()
    if not row:
        raise ValueError("Recipe not found")
    return row


async def learn_recipe(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    data: LearnRecipeRequest,
    *,
    owner_token: str,
    publisher: EventPublisher,
) -> DishTrialResponse:
    recipe = await get_curated_recipe(session, data.recipe_id)
    dish_name = (data.dish_name or recipe.title).strip()
    dish_id = await create_trial_dish(
        kitchen_id=kitchen_id,
        owner_token=owner_token,
        name=dish_name,
        price=data.price,
        description=recipe.description,
        ingredients_description=", ".join(recipe.ingredients) if recipe.ingredients else None,
        image_url=recipe.image_url,
        cuisine_id=data.cuisine_id,
        category_id=data.category_id,
        prep_time_min=data.prep_time_min,
    )
    trial = DishTrial(
        kitchen_id=kitchen_id,
        curated_recipe_id=recipe.id,
        catalog_dish_id=dish_id,
        dish_name=dish_name,
        status="draft",
        rating_threshold=DEFAULT_RATING_THRESHOLD,
    )
    session.add(trial)
    await session.flush()

    event = EventPublisher.build(
        event_type="recipe.learned",
        aggregate_type="trial",
        aggregate_id=str(trial.id),
        producer="learning-service",
        payload={
            "kitchen_id": str(kitchen_id),
            "trial_id": str(trial.id),
            "recipe_id": str(recipe.id),
            "dish_id": str(dish_id),
            "dish_name": dish_name,
        },
    )
    await publisher.publish(stream_key("learning", "trial"), event, session=session)
    return await trial_to_response(session, trial)


async def list_kitchen_trials(session: AsyncSession, kitchen_id: uuid.UUID) -> DishTrialListResponse:
    rows = list(
        (
            await session.execute(
                select(DishTrial)
                .where(DishTrial.kitchen_id == kitchen_id)
                .order_by(DishTrial.created_at.desc())
            )
        ).scalars().all()
    )
    trials = [await trial_to_response(session, t, include_invites=False) for t in rows]
    return DishTrialListResponse(trials=trials, total=len(trials))


async def get_kitchen_trial(
    session: AsyncSession, kitchen_id: uuid.UUID, trial_id: uuid.UUID
) -> DishTrialResponse:
    trial = await _load_trial(session, kitchen_id, trial_id)
    return await trial_to_response(session, trial, include_invites=True)


async def _load_trial(session: AsyncSession, kitchen_id: uuid.UUID, trial_id: uuid.UUID) -> DishTrial:
    trial = (
        await session.execute(
            select(DishTrial).where(DishTrial.id == trial_id, DishTrial.kitchen_id == kitchen_id)
        )
    ).scalar_one_or_none()
    if not trial:
        raise ValueError("Trial not found")
    return trial


async def trial_to_response(
    session: AsyncSession, trial: DishTrial, *, include_invites: bool = False
) -> DishTrialResponse:
    invites: list[TrialInviteResponse] = []
    if include_invites:
        inv_rows = list(
            (
                await session.execute(
                    select(TrialInvite).where(TrialInvite.trial_id == trial.id).order_by(TrialInvite.created_at)
                )
            ).scalars().all()
        )
        rating_map: dict[uuid.UUID, TrialRating] = {}
        if inv_rows:
            ratings = list(
                (
                    await session.execute(
                        select(TrialRating).where(
                            TrialRating.trial_id == trial.id,
                            TrialRating.invite_id.in_([i.id for i in inv_rows]),
                        )
                    )
                ).scalars().all()
            )
            rating_map = {r.invite_id: r for r in ratings}
        for inv in inv_rows:
            rating = rating_map.get(inv.id)
            invites.append(
                TrialInviteResponse(
                    id=inv.id,
                    customer_id=inv.customer_id,
                    customer_name=inv.customer_name,
                    customer_phone_masked=_mask_phone(inv.customer_phone),
                    status=inv.status,
                    home_taste_score=rating.home_taste_score if rating else None,
                    quality_score=rating.quality_score if rating else None,
                )
            )
    return DishTrialResponse(
        id=trial.id,
        kitchen_id=trial.kitchen_id,
        curated_recipe_id=trial.curated_recipe_id,
        catalog_dish_id=trial.catalog_dish_id,
        dish_name=trial.dish_name,
        status=trial.status,
        promo_type=trial.promo_type,
        sample_price=float(trial.sample_price) if trial.sample_price is not None else None,
        rating_threshold=float(trial.rating_threshold),
        avg_rating=float(trial.avg_rating) if trial.avg_rating is not None else None,
        invite_count=trial.invite_count,
        whatsapp_sent_at=trial.whatsapp_sent_at,
        promoted_at=trial.promoted_at,
        created_at=trial.created_at,
        invites=invites,
    )


async def _load_crm_customers(
    session: AsyncSession, kitchen_id: uuid.UUID, customer_ids: list[uuid.UUID]
) -> list[dict]:
    if not customer_ids:
        return []
    placeholders = ", ".join(f":c{i}" for i in range(len(customer_ids)))
    params: dict = {"kid": kitchen_id}
    for i, cid in enumerate(customer_ids):
        params[f"c{i}"] = cid
    result = await session.execute(
        text(
            f"""
            SELECT customer_id, customer_phone, customer_name
            FROM ckac_marketing.kitchen_customers
            WHERE kitchen_id = :kid AND customer_id IN ({placeholders})
            """
        ),
        params,
    )
    rows = [
        {"customer_id": r[0], "customer_phone": r[1], "customer_name": r[2]}
        for r in result.fetchall()
    ]
    if len(rows) != len(customer_ids):
        raise ValueError(f"Select {MIN_INVITES}–{MAX_INVITES} customers from your CRM list")
    return rows


async def set_trial_invites(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    trial_id: uuid.UUID,
    data: TrialInvitesRequest,
) -> DishTrialResponse:
    trial = await _load_trial(session, kitchen_id, trial_id)
    if trial.status not in ("draft", "sampling"):
        raise ValueError("Cannot change invites after sampling started")

    customers = await _load_crm_customers(session, kitchen_id, data.customer_ids)
    await session.execute(
        text("DELETE FROM ckac_learning.trial_invites WHERE trial_id = :tid"),
        {"tid": trial_id},
    )
    for c in customers:
        session.add(
            TrialInvite(
                trial_id=trial.id,
                customer_id=c["customer_id"],
                customer_phone=c["customer_phone"],
                customer_name=c["customer_name"],
                status="pending",
            )
        )
    trial.promo_type = data.promo_type
    trial.sample_price = data.sample_price
    trial.invite_count = len(customers)
    await session.flush()
    return await trial_to_response(session, trial, include_invites=True)


async def send_trial_samples(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    trial_id: uuid.UUID,
    *,
    publisher: EventPublisher,
) -> DishTrialResponse:
    trial = await _load_trial(session, kitchen_id, trial_id)
    if trial.invite_count < MIN_INVITES:
        raise ValueError(f"Add at least {MIN_INVITES} customer invites before sending")
    if trial.status == "promoted":
        raise ValueError("Trial already promoted")

    invites = list(
        (
            await session.execute(select(TrialInvite).where(TrialInvite.trial_id == trial.id))
        ).scalars().all()
    )
    offer = "free sample" if trial.promo_type == "free" else f"sample for ₹{trial.sample_price:.0f}"
    message = (
        f"Hi! {trial.dish_name} is ready for a kitchen trial — we'd love your feedback on this {offer}. "
        "Reply YES to taste and rate."
    )
    await notify_trial_sample_blast(
        kitchen_id=kitchen_id,
        trial_id=trial.id,
        dish_name=trial.dish_name,
        message=message,
        recipient_count=len(invites),
    )
    now = datetime.now(UTC)
    for inv in invites:
        inv.status = "sent"
    trial.status = "collecting_ratings"
    trial.whatsapp_sent_at = now
    await session.flush()

    event = EventPublisher.build(
        event_type="trial.sample_sent",
        aggregate_type="trial",
        aggregate_id=str(trial.id),
        producer="learning-service",
        payload={
            "kitchen_id": str(kitchen_id),
            "trial_id": str(trial.id),
            "invite_count": len(invites),
        },
    )
    await publisher.publish(stream_key("learning", "trial"), event, session=session)
    return await trial_to_response(session, trial, include_invites=True)


async def record_trial_rating(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    trial_id: uuid.UUID,
    data: TrialRatingRequest,
) -> DishTrialResponse:
    trial = await _load_trial(session, kitchen_id, trial_id)
    invite = (
        await session.execute(
            select(TrialInvite).where(
                TrialInvite.id == data.invite_id,
                TrialInvite.trial_id == trial.id,
            )
        )
    ).scalar_one_or_none()
    if not invite:
        raise ValueError("Invite not found for this trial")
    if invite.status == "rated":
        raise ValueError("Invite already rated")

    existing = (
        await session.execute(select(TrialRating).where(TrialRating.invite_id == invite.id))
    ).scalar_one_or_none()
    if existing:
        raise ValueError("Rating already recorded")

    session.add(
        TrialRating(
            trial_id=trial.id,
            invite_id=invite.id,
            home_taste_score=data.home_taste_score,
            quality_score=data.quality_score,
            feedback=data.feedback,
        )
    )
    invite.status = "rated"
    await session.flush()

    ratings = list(
        (
            await session.execute(select(TrialRating).where(TrialRating.trial_id == trial.id))
        ).scalars().all()
    )
    if ratings:
        scores = [_overall(r.home_taste_score, r.quality_score) for r in ratings]
        trial.avg_rating = round(sum(scores) / len(scores), 2)
    await session.flush()
    return await trial_to_response(session, trial, include_invites=True)


async def promote_trial(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    trial_id: uuid.UUID,
    *,
    owner_token: str,
    publisher: EventPublisher,
    force: bool = False,
) -> DishTrialResponse:
    trial = await _load_trial(session, kitchen_id, trial_id)
    if trial.status == "promoted":
        raise ValueError("Trial already promoted")
    if trial.avg_rating is None:
        raise ValueError("No ratings collected yet")
    threshold = float(trial.rating_threshold)
    if not force and float(trial.avg_rating) < threshold:
        raise ValueError(f"Average rating {trial.avg_rating} is below threshold {threshold}")

    await activate_dish(
        kitchen_id=kitchen_id,
        dish_id=trial.catalog_dish_id,
        owner_token=owner_token,
    )
    now = datetime.now(UTC)
    trial.status = "promoted"
    trial.promoted_at = now
    await session.flush()

    event = EventPublisher.build(
        event_type="trial.promoted",
        aggregate_type="trial",
        aggregate_id=str(trial.id),
        producer="learning-service",
        payload={
            "kitchen_id": str(kitchen_id),
            "trial_id": str(trial.id),
            "dish_id": str(trial.catalog_dish_id),
            "avg_rating": float(trial.avg_rating),
        },
    )
    await publisher.publish(stream_key("learning", "trial"), event, session=session)
    return await trial_to_response(session, trial, include_invites=True)
