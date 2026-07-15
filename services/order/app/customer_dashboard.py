"""Customer dashboard aggregate — orders enriched, savings, health, tips."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OrderItem
from app.schemas import OrderResponse, list_customer_orders, order_to_response


class EnrichedOrderItem(BaseModel):
    id: uuid.UUID
    dish_id: uuid.UUID
    dish_name: str
    quantity: int
    unit_price: float
    line_total: float
    cuisine_name: str | None = None
    diet: str | None = None
    media: list[dict[str, Any]] = Field(default_factory=list)
    restaurant_benchmark_price: float | None = None
    saved_vs_restaurant: float = 0


class DashboardOrder(BaseModel):
    order: OrderResponse
    items: list[EnrichedOrderItem]
    can_rate: bool
    tracking_token: str | None = None
    has_live_media: bool = False
    diets: list[str] = Field(default_factory=list)
    cuisines: list[str] = Field(default_factory=list)


class SavingsSummary(BaseModel):
    total_saved: float
    restaurant_equivalent_spend: float
    kitchcu_spend: float
    by_dish: list[dict[str, Any]]


class HealthSummary(BaseModel):
    veg_share_pct: float
    non_veg_share_pct: float
    vegan_share_pct: float
    home_freshness_score: float
    restaurant_processed_score: float
    note: str


class WellnessTip(BaseModel):
    after_dish: str | None = None
    walk_minutes: int
    water_ml: int
    message: str


class CustomerDashboardResponse(BaseModel):
    orders: list[DashboardOrder]
    savings: SavingsSummary
    health: HealthSummary
    tips: list[WellnessTip]
    filters: dict[str, list[str]]


def _benchmark_price(unit_price: float) -> float:
    """Estimate typical restaurant plate price for the same dish style."""
    return round(unit_price * 1.4 + 40.0, 2)


def _tips_for_items(items: list[EnrichedOrderItem]) -> list[WellnessTip]:
    tips: list[WellnessTip] = []
    for item in items[:5]:
        qty = max(1, item.quantity)
        diet = (item.diet or "").lower()
        if diet == "non_veg":
            walk, water = 20 * qty, 350 * qty
            msg = "After a richer meal, a short walk and water help digestion."
        elif diet == "vegan":
            walk, water = 12 * qty, 300 * qty
            msg = "Plant-forward plate — stay hydrated and take a light stroll."
        else:
            walk, water = 15 * qty, 300 * qty
            msg = "Home-cooked portions digest easier — walk and sip water steadily."
        tips.append(
            WellnessTip(
                after_dish=item.dish_name,
                walk_minutes=min(45, walk),
                water_ml=min(750, water),
                message=msg,
            )
        )
    if not tips:
        tips.append(
            WellnessTip(
                after_dish=None,
                walk_minutes=15,
                water_ml=300,
                message="After any meal, aim for a 15-minute walk and ~300 ml water.",
            )
        )
    return tips


async def build_customer_dashboard(
    session: AsyncSession,
    customer_phone: str,
    *,
    diet: str | None = None,
    cuisine: str | None = None,
    live_media_only: bool = False,
) -> CustomerDashboardResponse:
    orders = await list_customer_orders(session, customer_phone)
    if not orders:
        return CustomerDashboardResponse(
            orders=[],
            savings=SavingsSummary(
                total_saved=0, restaurant_equivalent_spend=0, kitchcu_spend=0, by_dish=[]
            ),
            health=HealthSummary(
                veg_share_pct=0,
                non_veg_share_pct=0,
                vegan_share_pct=0,
                home_freshness_score=60,
                restaurant_processed_score=55,
                note="Order home kitchens to build your health and savings picture.",
            ),
            tips=_tips_for_items([]),
            filters={"cuisines": [], "diets": []},
        )

    order_ids = [o.id for o in orders]
    items_result = await session.execute(select(OrderItem).where(OrderItem.order_id.in_(order_ids)))
    items_by_order: dict[uuid.UUID, list[OrderItem]] = {}
    for item in items_result.scalars().all():
        items_by_order.setdefault(item.order_id, []).append(item)

    dish_ids = {item.dish_id for items in items_by_order.values() for item in items}
    catalog: dict[uuid.UUID, dict] = {}
    if dish_ids:
        result = await session.execute(
            text(
                """
                SELECT d.id, c.slug AS category_slug, cu.name AS cuisine_name,
                       COALESCE(
                         (
                           SELECT json_agg(json_build_object(
                             'url', m.url,
                             'is_live_capture', m.is_live_capture,
                             'is_hero', m.is_hero,
                             'captured_at', m.captured_at
                           ) ORDER BY m.is_hero DESC)
                           FROM ckac_catalog.dish_media m
                           WHERE m.dish_id = d.id
                         ),
                         '[]'::json
                       ) AS media
                FROM ckac_catalog.dishes d
                LEFT JOIN ckac_catalog.categories c ON c.id = d.category_id
                LEFT JOIN ckac_catalog.cuisines cu ON cu.id = d.cuisine_id
                WHERE d.id = ANY(:ids)
                """
            ),
            {"ids": list(dish_ids)},
        )
        for row in result.mappings().all():
            catalog[row["id"]] = dict(row)

    dash_orders: list[DashboardOrder] = []
    savings_by_dish: dict[str, float] = {}
    total_saved = 0.0
    restaurant_eq = 0.0
    kitchcu_spend = 0.0
    diet_counts = {"veg": 0, "non_veg": 0, "vegan": 0, "other": 0}
    all_cuisines: set[str] = set()
    all_diets: set[str] = set()
    tip_source_items: list[EnrichedOrderItem] = []

    for order in orders:
        enriched_items: list[EnrichedOrderItem] = []
        order_diets: set[str] = set()
        order_cuisines: set[str] = set()
        has_live = False
        for item in items_by_order.get(order.id, []):
            meta = catalog.get(item.dish_id, {})
            media = list(meta.get("media") or [])
            if isinstance(media, str):
                media = []
            if any(m.get("is_live_capture") for m in media if isinstance(m, dict)):
                has_live = True
            diet_slug = meta.get("category_slug") or "other"
            cuisine_name = meta.get("cuisine_name")
            if cuisine_name:
                order_cuisines.add(cuisine_name)
                all_cuisines.add(cuisine_name)
            if diet_slug:
                order_diets.add(diet_slug)
                all_diets.add(diet_slug)
            unit = float(item.unit_price)
            line_total = unit * int(item.quantity)
            bench = _benchmark_price(unit)
            saved = max(0.0, (bench - unit) * item.quantity)
            total_saved += saved
            restaurant_eq += bench * item.quantity
            kitchcu_spend += line_total
            savings_by_dish[item.dish_name] = savings_by_dish.get(item.dish_name, 0.0) + saved
            bucket = diet_slug if diet_slug in diet_counts else "other"
            diet_counts[bucket] += item.quantity
            ei = EnrichedOrderItem(
                id=item.id,
                dish_id=item.dish_id,
                dish_name=item.dish_name,
                quantity=item.quantity,
                unit_price=unit,
                line_total=line_total,
                cuisine_name=cuisine_name,
                diet=diet_slug,
                media=[m for m in media if isinstance(m, dict)],
                restaurant_benchmark_price=bench,
                saved_vs_restaurant=round(saved, 2),
            )
            enriched_items.append(ei)
            if order.status == "delivered":
                tip_source_items.append(ei)

        if diet and diet not in order_diets:
            continue
        if cuisine and cuisine not in order_cuisines:
            continue
        if live_media_only and not has_live:
            continue

        order_resp = await order_to_response(session, order)
        dash_orders.append(
            DashboardOrder(
                order=order_resp,
                items=enriched_items,
                can_rate=order.status == "delivered",
                tracking_token=order.tracking_token,
                has_live_media=has_live,
                diets=sorted(order_diets),
                cuisines=sorted(order_cuisines),
            )
        )

    total_portions = sum(diet_counts.values()) or 1
    veg_pct = round(100 * diet_counts["veg"] / total_portions, 1)
    non_pct = round(100 * diet_counts["non_veg"] / total_portions, 1)
    vegan_pct = round(100 * diet_counts["vegan"] / total_portions, 1)
    home_score = min(95.0, 55.0 + veg_pct * 0.25 + vegan_pct * 0.2)
    restaurant_score = max(25.0, 70.0 - veg_pct * 0.15)

    return CustomerDashboardResponse(
        orders=dash_orders,
        savings=SavingsSummary(
            total_saved=round(total_saved, 2),
            restaurant_equivalent_spend=round(restaurant_eq, 2),
            kitchcu_spend=round(kitchcu_spend, 2),
            by_dish=[
                {"dish_name": name, "saved": round(val, 2)}
                for name, val in sorted(savings_by_dish.items(), key=lambda x: -x[1])[:12]
            ],
        ),
        health=HealthSummary(
            veg_share_pct=veg_pct,
            non_veg_share_pct=non_pct,
            vegan_share_pct=vegan_pct,
            home_freshness_score=round(home_score, 1),
            restaurant_processed_score=round(restaurant_score, 1),
            note=(
                "Home kitchens typically use lighter oil and live-prep ingredients versus "
                "restaurant batch cooking — scores estimate relative patterns from your order mix."
            ),
        ),
        tips=_tips_for_items(tip_source_items[-8:]),
        filters={
            "cuisines": sorted(all_cuisines),
            "diets": sorted(all_diets),
        },
    )
