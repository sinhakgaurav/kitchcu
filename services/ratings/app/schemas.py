"""Ratings domain — verified purchase ratings, aggregates, A/V reviews (F16–F18)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DishRating, DishRatingAggregate, DishSuggestion
from ckac_common.auth import stream_key
from ckac_common.event_bus import EventPublisher

HOME_TASTE_WEIGHT = 0.6
QUALITY_WEIGHT = 0.4


class RatingItemInput(BaseModel):
    """One dish's rating within an order-level rating submission (F16)."""

    dish_id: uuid.UUID = Field(..., description="Dish being rated; must have been part of the order.")
    home_taste_score: int = Field(ge=1, le=5, description="1-5 — how close the dish tasted to authentic home cooking.", examples=[5])
    quality_score: int = Field(ge=1, le=5, description="1-5 — overall food quality/execution.", examples=[4])
    media_url: str | None = Field(default=None, max_length=2048, description="Optional uploaded audio/video review URL. Must be paired with `media_type`.")
    media_type: Literal["video", "audio"] | None = Field(default=None, description="Media kind for `media_url`. Required if `media_url` is set, omitted otherwise.")
    is_anonymous: bool = Field(default=True, description="Whether the A/V review (if any) is shown to other customers without attribution.")

    @model_validator(mode="after")
    def media_pair(self) -> RatingItemInput:
        if bool(self.media_url) != bool(self.media_type):
            raise ValueError("media_url and media_type must both be set or both omitted")
        return self


class OrderRatingsCreateRequest(BaseModel):
    """Customer request to rate 1-20 dishes from a single delivered order."""

    ratings: list[RatingItemInput] = Field(min_length=1, max_length=20, description="One entry per dish being rated, up to 20.")


class DishRatingResponse(BaseModel):
    """A single submitted dish rating."""

    id: uuid.UUID = Field(..., description="Rating row UUID.")
    dish_id: uuid.UUID = Field(..., description="Rated dish UUID.")
    order_id: uuid.UUID = Field(..., description="Order this rating is tied to — always a delivered order.")
    home_taste_score: int = Field(..., description="1-5 home-taste score.")
    quality_score: int = Field(..., description="1-5 quality score.")
    media_url: str | None = Field(default=None, description="Attached A/V review URL, if any.")
    media_type: str | None = Field(default=None, description="'video' or 'audio', if media attached.")
    is_anonymous: bool = Field(..., description="Whether the review is shown anonymously.")
    created_at: datetime = Field(..., description="Submission timestamp, UTC.")

    model_config = {"from_attributes": True}


class OrderRatingsCreateResponse(BaseModel):
    """Result of submitting ratings for an order."""

    ratings: list[DishRatingResponse] = Field(..., description="The created rating rows, one per dish rated.")


class DishRatingSummaryResponse(BaseModel):
    """Live-aggregated rating summary for one dish."""

    dish_id: uuid.UUID = Field(..., description="Dish UUID.")
    rating_count: int = Field(..., description="Total verified ratings received. `0` if unrated.")
    avg_home_taste: float = Field(..., description="Average home-taste score across all ratings.", examples=[4.6])
    avg_quality: float = Field(..., description="Average quality score across all ratings.", examples=[4.3])
    overall_rating: float = Field(..., description="Weighted overall score: 60% home-taste + 40% quality.", examples=[4.48])


class KitchenRatingSummariesResponse(BaseModel):
    """Rating summaries for every rated dish in a kitchen."""

    summaries: list[DishRatingSummaryResponse] = Field(..., description="One summary per dish that has at least one rating.")


class AnonymousReviewResponse(BaseModel):
    """Public, customer-facing review card shown on a dish's page."""

    id: uuid.UUID = Field(..., description="Rating row UUID.")
    home_taste_score: int = Field(..., description="1-5 home-taste score.")
    quality_score: int = Field(..., description="1-5 quality score.")
    media_url: str | None = Field(default=None, description="Attached A/V review URL, if any.")
    media_type: str | None = Field(default=None, description="'video' or 'audio', if media attached.")
    created_at: datetime = Field(..., description="Submission timestamp, UTC.")


class AnonymousReviewsListResponse(BaseModel):
    """Page of public reviews for a dish, newest first."""

    reviews: list[AnonymousReviewResponse] = Field(..., description="Approved reviews, most recent first.")
    total: int = Field(..., description="Number of reviews returned in this page.")


class DishSuggestionCreateRequest(BaseModel):
    """Customer feedback/suggestion tied to a dish (e.g. requesting a tweak or a new variant)."""

    suggestion_text: str = Field(min_length=5, max_length=1000, description="Freeform suggestion text.", examples=["Could you make a less spicy version of this?"])
    order_id: uuid.UUID | None = Field(default=None, description="Order this suggestion relates to, if any (not required to be delivered).")


class DishSuggestionUpdateRequest(BaseModel):
    """Owner decision on a customer's dish suggestion."""

    status: Literal["accepted", "rejected"] = Field(..., description="Owner's decision on the suggestion.")
    owner_response: str | None = Field(default=None, max_length=2000, description="Optional owner reply shown back to the customer.")


class DishSuggestionResponse(BaseModel):
    """A customer's dish suggestion and its current owner-review status."""

    id: uuid.UUID = Field(..., description="Suggestion UUID.")
    kitchen_id: uuid.UUID = Field(..., description="Kitchen the dish belongs to.")
    dish_id: uuid.UUID = Field(..., description="Dish the suggestion is about.")
    dish_name: str | None = Field(default=None, description="Dish name, resolved for display.")
    customer_id: uuid.UUID = Field(..., description="Customer who submitted the suggestion.")
    order_id: uuid.UUID | None = Field(default=None, description="Related order, if provided at submission.")
    suggestion_text: str = Field(..., description="Suggestion text.")
    status: str = Field(..., description="'pending', 'accepted', or 'rejected'.")
    owner_response: str | None = Field(default=None, description="Owner's reply, if any.")
    created_at: datetime = Field(..., description="Submission timestamp, UTC.")

    model_config = {"from_attributes": True}


class DishSuggestionListResponse(BaseModel):
    """Suggestion roster for a kitchen (owner view)."""

    suggestions: list[DishSuggestionResponse] = Field(..., description="Suggestions ordered newest first.")
    total: int = Field(..., description="Number of suggestions returned.")


def _overall_rating(avg_home: float, avg_quality: float) -> float:
    return round(HOME_TASTE_WEIGHT * avg_home + QUALITY_WEIGHT * avg_quality, 2)


def rating_to_response(row: DishRating) -> DishRatingResponse:
    return DishRatingResponse(
        id=row.id,
        dish_id=row.dish_id,
        order_id=row.order_id,
        home_taste_score=int(row.home_taste_score),
        quality_score=int(row.quality_score),
        media_url=row.media_url,
        media_type=row.media_type,
        is_anonymous=bool(row.is_anonymous),
        created_at=row.created_at,
    )


def aggregate_to_summary(row: DishRatingAggregate) -> DishRatingSummaryResponse:
    return DishRatingSummaryResponse(
        dish_id=row.dish_id,
        rating_count=int(row.rating_count),
        avg_home_taste=round(float(row.avg_home_taste), 2),
        avg_quality=round(float(row.avg_quality), 2),
        overall_rating=round(float(row.overall_rating), 2),
    )


async def _verify_delivered_order(
    session: AsyncSession,
    order_id: uuid.UUID,
    customer_phone: str,
) -> dict:
    result = await session.execute(
        text(
            """
            SELECT id, kitchen_id, status, customer_phone
            FROM ckac_orders.orders
            WHERE id = :oid
            LIMIT 1
            """
        ),
        {"oid": order_id},
    )
    row = result.mappings().one_or_none()
    if not row:
        raise ValueError("Order not found")
    if row["status"] != "delivered":
        raise ValueError("Only delivered orders can be rated")
    if row["customer_phone"] != customer_phone:
        raise ValueError("Order not found")
    return dict(row)


async def _dish_in_order(session: AsyncSession, order_id: uuid.UUID, dish_id: uuid.UUID) -> bool:
    result = await session.execute(
        text(
            "SELECT 1 FROM ckac_orders.order_items "
            "WHERE order_id = :oid AND dish_id = :did LIMIT 1"
        ),
        {"oid": order_id, "did": dish_id},
    )
    return result.scalar_one_or_none() is not None


async def _update_aggregate(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    dish_id: uuid.UUID,
    home_taste: int,
    quality: int,
    publisher: EventPublisher,
) -> DishRatingAggregate:
    result = await session.execute(
        select(DishRatingAggregate).where(DishRatingAggregate.dish_id == dish_id)
    )
    agg = result.scalar_one_or_none()
    now = datetime.now(UTC)
    if agg:
        count = int(agg.rating_count) + 1
        avg_home = (float(agg.avg_home_taste) * int(agg.rating_count) + home_taste) / count
        avg_quality = (float(agg.avg_quality) * int(agg.rating_count) + quality) / count
        agg.rating_count = count
        agg.avg_home_taste = round(avg_home, 2)
        agg.avg_quality = round(avg_quality, 2)
        agg.overall_rating = _overall_rating(avg_home, avg_quality)
        agg.updated_at = now
    else:
        agg = DishRatingAggregate(
            kitchen_id=kitchen_id,
            dish_id=dish_id,
            rating_count=1,
            avg_home_taste=float(home_taste),
            avg_quality=float(quality),
            overall_rating=_overall_rating(float(home_taste), float(quality)),
            updated_at=now,
        )
        session.add(agg)
    await session.flush()

    event = EventPublisher.build(
        event_type="rating.aggregate.updated",
        aggregate_type="dish_rating_aggregate",
        aggregate_id=str(dish_id),
        producer="ratings-service",
        payload={
            "kitchen_id": str(kitchen_id),
            "dish_id": str(dish_id),
            "rating_count": int(agg.rating_count),
            "overall_rating": float(agg.overall_rating),
        },
    )
    await publisher.publish(stream_key("ratings", "dish"), event, session=session)
    return agg


async def submit_order_ratings(
    session: AsyncSession,
    order_id: uuid.UUID,
    customer_id: uuid.UUID,
    customer_phone: str,
    body: OrderRatingsCreateRequest,
    publisher: EventPublisher,
) -> OrderRatingsCreateResponse:
    order = await _verify_delivered_order(session, order_id, customer_phone)
    kitchen_id = order["kitchen_id"]
    created: list[DishRating] = []

    for item in body.ratings:
        if not await _dish_in_order(session, order_id, item.dish_id):
            raise ValueError(f"Dish {item.dish_id} was not in this order")

        existing = await session.execute(
            select(DishRating).where(
                DishRating.order_id == order_id,
                DishRating.dish_id == item.dish_id,
                DishRating.customer_id == customer_id,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Already rated dish {item.dish_id} for this order")

        rating = DishRating(
            kitchen_id=kitchen_id,
            dish_id=item.dish_id,
            order_id=order_id,
            customer_id=customer_id,
            home_taste_score=item.home_taste_score,
            quality_score=item.quality_score,
            media_url=item.media_url,
            media_type=item.media_type,
            is_anonymous=item.is_anonymous,
        )
        session.add(rating)
        await session.flush()
        created.append(rating)

        await _update_aggregate(
            session,
            kitchen_id,
            item.dish_id,
            item.home_taste_score,
            item.quality_score,
            publisher,
        )

        event = EventPublisher.build(
            event_type="rating.created",
            aggregate_type="dish_rating",
            aggregate_id=str(rating.id),
            producer="ratings-service",
            payload={
                "kitchen_id": str(kitchen_id),
                "dish_id": str(item.dish_id),
                "order_id": str(order_id),
                "home_taste_score": item.home_taste_score,
                "quality_score": item.quality_score,
                "has_media": bool(item.media_url),
            },
        )
        await publisher.publish(stream_key("ratings", "rating"), event, session=session)

    return OrderRatingsCreateResponse(ratings=[rating_to_response(r) for r in created])


async def get_dish_summary(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    dish_id: uuid.UUID,
) -> DishRatingSummaryResponse:
    result = await session.execute(
        select(DishRatingAggregate).where(
            DishRatingAggregate.kitchen_id == kitchen_id,
            DishRatingAggregate.dish_id == dish_id,
        )
    )
    agg = result.scalar_one_or_none()
    if not agg:
        return DishRatingSummaryResponse(
            dish_id=dish_id,
            rating_count=0,
            avg_home_taste=0.0,
            avg_quality=0.0,
            overall_rating=0.0,
        )
    return aggregate_to_summary(agg)


async def list_kitchen_summaries(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
) -> KitchenRatingSummariesResponse:
    result = await session.execute(
        select(DishRatingAggregate).where(DishRatingAggregate.kitchen_id == kitchen_id)
    )
    rows = result.scalars().all()
    return KitchenRatingSummariesResponse(summaries=[aggregate_to_summary(r) for r in rows])


async def list_anonymous_reviews(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    dish_id: uuid.UUID,
    *,
    limit: int = 20,
) -> AnonymousReviewsListResponse:
    result = await session.execute(
        select(DishRating)
        .where(
            DishRating.kitchen_id == kitchen_id,
            DishRating.dish_id == dish_id,
            DishRating.moderation_status == "approved",
        )
        .order_by(DishRating.created_at.desc())
        .limit(limit)
    )
    rows = result.scalars().all()
    reviews = [
        AnonymousReviewResponse(
            id=r.id,
            home_taste_score=int(r.home_taste_score),
            quality_score=int(r.quality_score),
            media_url=r.media_url if r.is_anonymous else r.media_url,
            media_type=r.media_type,
            created_at=r.created_at,
        )
        for r in rows
        if r.media_url or r.home_taste_score
    ]
    return AnonymousReviewsListResponse(reviews=reviews, total=len(reviews))


async def _load_dish_kitchen(session: AsyncSession, dish_id: uuid.UUID) -> uuid.UUID:
    result = await session.execute(
        text("SELECT kitchen_id FROM ckac_catalog.dishes WHERE id = :did LIMIT 1"),
        {"did": dish_id},
    )
    kitchen_id = result.scalar_one_or_none()
    if not kitchen_id:
        raise ValueError("Dish not found")
    return kitchen_id


async def create_suggestion(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    dish_id: uuid.UUID,
    customer_id: uuid.UUID,
    body: DishSuggestionCreateRequest,
) -> DishSuggestion:
    dish_kitchen = await _load_dish_kitchen(session, dish_id)
    if dish_kitchen != kitchen_id:
        raise ValueError("Dish does not belong to this kitchen")

    suggestion = DishSuggestion(
        kitchen_id=kitchen_id,
        dish_id=dish_id,
        customer_id=customer_id,
        order_id=body.order_id,
        suggestion_text=body.suggestion_text.strip(),
    )
    session.add(suggestion)
    await session.flush()
    return suggestion


async def list_suggestions(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    *,
    status: str | None = None,
) -> DishSuggestionListResponse:
    query = select(DishSuggestion).where(DishSuggestion.kitchen_id == kitchen_id)
    if status:
        query = query.where(DishSuggestion.status == status)
    query = query.order_by(DishSuggestion.created_at.desc())
    result = await session.execute(query)
    rows = result.scalars().all()

    dish_names: dict[uuid.UUID, str] = {}
    if rows:
        ids = list({r.dish_id for r in rows})
        name_rows = (
            await session.execute(
                text("SELECT id, name FROM ckac_catalog.dishes WHERE id = ANY(:ids)"),
                {"ids": ids},
            )
        ).mappings().all()
        dish_names = {r["id"]: r["name"] for r in name_rows}

    return DishSuggestionListResponse(
        suggestions=[
            DishSuggestionResponse(
                id=r.id,
                kitchen_id=r.kitchen_id,
                dish_id=r.dish_id,
                dish_name=dish_names.get(r.dish_id),
                customer_id=r.customer_id,
                order_id=r.order_id,
                suggestion_text=r.suggestion_text,
                status=r.status,
                owner_response=r.owner_response,
                created_at=r.created_at,
            )
            for r in rows
        ],
        total=len(rows),
    )


async def update_suggestion(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    suggestion_id: uuid.UUID,
    body: DishSuggestionUpdateRequest,
) -> DishSuggestionResponse:
    result = await session.execute(
        select(DishSuggestion).where(
            DishSuggestion.id == suggestion_id,
            DishSuggestion.kitchen_id == kitchen_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise ValueError("Suggestion not found")
    row.status = body.status
    row.owner_response = body.owner_response
    await session.flush()

    name_result = await session.execute(
        text("SELECT name FROM ckac_catalog.dishes WHERE id = :did LIMIT 1"),
        {"did": row.dish_id},
    )
    dish_name = name_result.scalar_one_or_none()

    return DishSuggestionResponse(
        id=row.id,
        kitchen_id=row.kitchen_id,
        dish_id=row.dish_id,
        dish_name=dish_name,
        customer_id=row.customer_id,
        order_id=row.order_id,
        suggestion_text=row.suggestion_text,
        status=row.status,
        owner_response=row.owner_response,
        created_at=row.created_at,
    )
