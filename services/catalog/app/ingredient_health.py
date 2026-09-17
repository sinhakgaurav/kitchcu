"""P50 — dish health from F19 recipe ingredients (typical home-kitchen use, not medical advice)."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Dish, DishIngredient, Ingredient
from ckac_common.platform_config import is_feature_enabled

HEALTH_FEATURE = "dish_health"

_ALIAS_RE = re.compile(r"[^a-z0-9]+")


def normalize_ingredient_name(raw: str) -> str:
    return _ALIAS_RE.sub(" ", (raw or "").strip().lower()).strip()


@dataclass(frozen=True)
class HealthProfile:
    name: str
    score: int
    benefits: str
    disadvantages: str


def _p(name: str, score: int, benefits: str, disadvantages: str, *aliases: str) -> dict[str, HealthProfile]:
    profile = HealthProfile(name=name, score=score, benefits=benefits, disadvantages=disadvantages)
    keys = {normalize_ingredient_name(name), *(normalize_ingredient_name(a) for a in aliases)}
    return {key: profile for key in keys if key}


# Typical Indian home-kitchen use. Scores are heuristics for relative plate balance, not lab nutrition.
HEALTH_LIBRARY: dict[str, HealthProfile] = {}
for _chunk in (
    _p(
        "Spinach",
        88,
        "Leafy iron and fibre; common in home palak dishes with little processing.",
        "Oxalates can bother some people; heavy cream/butter in the gravy offsets the greens.",
        "palak",
    ),
    _p(
        "Mixed Vegetables",
        86,
        "Variety of fibre and micronutrients when cooked fresh rather than deep-fried.",
        "Overcooking or sugary sauces reduce the benefit.",
        "vegetables",
        "mixed veg",
    ),
    _p(
        "Cauliflower",
        84,
        "Low-energy vegetable used in home sabzis; fills the plate without much processing.",
        "Often fried as pakora; that cooking method is heavier than a dry sabzi.",
        "gobi",
    ),
    _p(
        "Tomato",
        82,
        "Lycopene and acidity that build home gravies without needing packaged sauce.",
        "Store puree can add salt and sugar; very sour plates may not suit acid reflux.",
    ),
    _p(
        "Capsicum",
        80,
        "Crunch and vitamin C in tikka and stir-fries when used fresh.",
        "Usually a garnish by weight — does not offset a butter-heavy gravy.",
        "bell pepper",
        "shimla mirch",
    ),
    _p(
        "Apple",
        80,
        "Fibre and natural sweetness in home desserts versus purely sugary fillings.",
        "Pastry, butter, and added sugar around the fruit dominate the plate.",
    ),
    _p(
        "Onion",
        78,
        "Base of most home tadkas; adds flavour so less packaged masala is needed.",
        "Deep-fried birista is calorie-dense; raw onion can be harsh on sensitive stomachs.",
    ),
    _p(
        "Lentils",
        84,
        "Everyday dal protein and fibre; a home-kitchen staple with light tadka.",
        "Excess ghee/butter tadka and fried papad on the side make the meal heavier.",
        "dal",
        "masoor",
        "toor dal",
    ),
    _p(
        "Chickpeas",
        82,
        "Plant protein and fibre in chana and bowls; filling without much processing.",
        "Deep-fried snacks (chana bhatura style sides) change the picture.",
        "chana",
        "kabuli chana",
    ),
    _p(
        "Tofu",
        80,
        "Mild plant protein used in bowls instead of cream-heavy gravies.",
        "Often fried; packaged tofu can be salty.",
    ),
    _p(
        "Yogurt",
        76,
        "Cultured dairy used in marinades and raita; gentler than cream for many plates.",
        "Full-fat dahi is still rich; sweet lassi-style sugar is a different use.",
        "dahi",
        "curd",
        "hung curd",
    ),
    _p(
        "Eggs",
        74,
        "Complete protein in home bhurji and bowls; simple cooking keeps it light.",
        "Frying in lots of oil or pairing with processed meats makes it heavier.",
        "egg",
    ),
    _p(
        "Milk",
        70,
        "Calcium and protein in chai and gravies when used as fresh milk.",
        "Full-cream milk plus sugar in drinks adds up quickly.",
    ),
    _p(
        "Paneer",
        68,
        "Home-style protein from milk; tikka uses yogurt marinade rather than batter fry.",
        "High in saturated fat; cream gravies and frying raise the load.",
    ),
    _p(
        "Chicken",
        66,
        "Leaner than red meat in home gravies and biryani when not deep-fried.",
        "Skin, cream, and butter chicken-style sauces make it a richer plate.",
    ),
    _p(
        "Potato",
        64,
        "Filling home sabzi staple; boiled or lightly sautéed is the usual kitchen style.",
        "Deep-fried samosa/chips versions are much heavier; high glycemic load.",
        "aloo",
    ),
    _p(
        "Basmati Rice",
        62,
        "Aromatic grain for biryani and fried rice; home portions are usually one cup cooked.",
        "Refined grain; large portions plus fried onions raise energy density.",
        "rice",
        "cooked rice",
    ),
    _p(
        "Rice Flour",
        60,
        "Used in dosa/idli-style batters at home instead of maida snacks.",
        "Still a refined starch; fried dosa with lots of oil is heavier.",
    ),
    _p(
        "Mutton",
        58,
        "Traditional home celebration protein; used in smaller gravies than restaurant platters.",
        "Higher saturated fat than chicken; slow-cooked fat should be skimmed.",
        "lamb",
        "goat",
    ),
    _p(
        "Wheat Flour",
        58,
        "Roti atta is a daily home staple versus maida bakery bread.",
        "Refined maida in pizza/samosa pastry is less fibre-dense than whole wheat roti.",
        "atta",
        "maida",
        "flour",
    ),
    _p(
        "Haldi",
        78,
        "Turmeric in almost every home tadka; used in pinches for colour and tradition.",
        "A pinch does not make a buttery gravy ‘healthy’; stains and bitter if overused.",
        "turmeric",
    ),
    _p(
        "Cinnamon",
        76,
        "Warm spice in small amounts for apple desserts and masala.",
        "Sugar and pastry around it drive the dessert’s load, not the bark.",
        "dalchini",
    ),
    _p(
        "Garam Masala",
        70,
        "Whole-spice blend that seasons home food without packaged sauces.",
        "Often paired with oil/ghee; the masala itself is not a health food in large spoons.",
    ),
    _p(
        "Tea Leaves",
        68,
        "Home chai in modest cups; antioxidants in the leaf.",
        "Milk + sugar chai several times a day adds sugar load.",
        "tea",
        "chai",
    ),
    _p(
        "Lal Mirch",
        62,
        "Heat and colour from chilli powder in home tikka and gravies.",
        "Can irritate acid reflux and piles; extra oil often comes with spicy restaurant-style fry.",
        "chilli powder",
        "red chilli",
        "mirch",
    ),
    _p(
        "Coffee Powder",
        55,
        "Small home cups; moderate caffeine.",
        "Sugar, creamers, and late-night cups affect sleep; acidity for some people.",
        "coffee",
    ),
    _p(
        "Mango Pulp",
        48,
        "Fruit base for aamras-style drinks when unsweetened.",
        "Tinned pulp is often sweetened; a large glass is mostly sugar.",
    ),
    _p(
        "Butter",
        42,
        "Flavour in home tadka and roti — usually teaspoons, not restaurant ladles.",
        "Saturated fat; butter chicken / pav bhaji style amounts add up fast.",
        "makhan",
        "ghee",
    ),
    _p(
        "Pav Bread",
        40,
        "Soft bun for bhaji; a couple of pav is a street-home treat.",
        "Refined maida; butter-toasted pav is energy-dense.",
        "pav",
        "bread",
    ),
    _p(
        "Khoya",
        38,
        "Milk solids for home mithai on festivals — small pieces.",
        "Very energy-dense; sugar + khoya sweets are occasional, not daily plates.",
        "mawa",
    ),
    _p(
        "Sugar",
        28,
        "Used sparingly in home chai and desserts.",
        "Adds energy without fibre; desserts and sweetened pulp dominate the score when quantity is high.",
        "chini",
    ),
):
    HEALTH_LIBRARY.update(_chunk)


def lookup_health_profile(name: str) -> HealthProfile | None:
    key = normalize_ingredient_name(name)
    if not key:
        return None
    if key in HEALTH_LIBRARY:
        return HEALTH_LIBRARY[key]
    # Last-token fallback: "Amul Paneer" / "Farm Fresh Tomato"
    parts = key.split()
    for i in range(len(parts)):
        candidate = " ".join(parts[i:])
        if candidate in HEALTH_LIBRARY:
            return HEALTH_LIBRARY[candidate]
    return None


def _line_weight(quantity: float, unit: str) -> float:
    qty = max(float(quantity or 0), 0.0)
    u = (unit or "g").strip().lower()
    if u in {"pcs", "pc", "piece", "pieces"}:
        return max(qty * 50.0, 0.1)
    return max(qty, 0.1)


def health_label(score: int | None) -> str:
    if score is None:
        return "Recipe not mapped"
    if score >= 80:
        return "Produce-forward"
    if score >= 65:
        return "Balanced plate"
    if score >= 50:
        return "Hearty plate"
    return "Richer plate"


class IngredientHealthLine(BaseModel):
    name: str
    score: int
    benefits: str
    disadvantages: str
    quantity: float | None = None
    unit: str | None = None
    kcal: float | None = None


class DishHealthSnapshot(BaseModel):
    dish_id: uuid.UUID | None = None
    dish_name: str | None = None
    kitchen_id: uuid.UUID | None = None
    score: int | None = None
    label: str
    mapped: int = 0
    total: int = 0
    ingredients: list[IngredientHealthLine] = Field(default_factory=list)
    calories_kcal: int | None = None
    calories_description: str | None = None
    calories_incomplete: bool = False
    healthy_tag: bool = False
    disclaimer: str = (
        "Typical home-kitchen use from the recipe map — not medical advice or a lab nutrition label."
    )


class DishHealthListResponse(BaseModel):
    dishes: list[DishHealthSnapshot]
    total: int


def score_ingredient_lines(lines: list[tuple[str, float, str]]) -> DishHealthSnapshot:
    """lines: (name, quantity, unit)."""
    matched: list[tuple[HealthProfile, float, float, str]] = []
    total = 0
    for name, qty, unit in lines:
        total += 1
        profile = lookup_health_profile(name)
        if not profile:
            continue
        matched.append((profile, _line_weight(qty, unit), float(qty), unit))
    if not matched:
        return DishHealthSnapshot(score=None, label=health_label(None), mapped=0, total=total)

    weight_sum = sum(w for _, w, _, _ in matched)
    raw = sum(p.score * w for p, w, _, _ in matched) / weight_sum
    score = int(round(raw))
    ingredients = [
        IngredientHealthLine(
            name=p.name,
            score=p.score,
            benefits=p.benefits,
            disadvantages=p.disadvantages,
            quantity=qty,
            unit=unit,
        )
        for p, _, qty, unit in matched
    ]
    # Stable unique-by-name, keep first (highest weight already in mean)
    seen: set[str] = set()
    unique: list[IngredientHealthLine] = []
    for line in sorted(ingredients, key=lambda x: -(x.quantity or 0)):
        if line.name in seen:
            continue
        seen.add(line.name)
        unique.append(line)
    return DishHealthSnapshot(
        score=score,
        label=health_label(score),
        mapped=len(unique),
        total=total,
        ingredients=unique,
    )


def aggregate_order_health(
    dish_snaps: list[tuple[DishHealthSnapshot, int]],
) -> DishHealthSnapshot:
    """Quantity-weighted mean of dish scores. dish_snaps: (snapshot, order qty)."""
    weighted: list[tuple[int, float]] = []
    all_lines: list[IngredientHealthLine] = []
    for snap, qty in dish_snaps:
        if snap.score is None:
            continue
        weighted.append((snap.score, float(max(qty, 1))))
        all_lines.extend(snap.ingredients)
    if not weighted:
        return DishHealthSnapshot(score=None, label=health_label(None), mapped=0, total=0)
    score = int(round(sum(s * w for s, w in weighted) / sum(w for _, w in weighted)))
    seen: set[str] = set()
    unique: list[IngredientHealthLine] = []
    for line in all_lines:
        if line.name in seen:
            continue
        seen.add(line.name)
        unique.append(line)
    return DishHealthSnapshot(
        score=score,
        label=health_label(score),
        mapped=len(unique),
        total=len(unique),
        ingredients=unique,
    )


async def load_recipe_lines(
    session: AsyncSession,
    dish_ids: list[uuid.UUID],
) -> dict[uuid.UUID, list[tuple[str, float, str, float | None, str]]]:
    """name, recipe qty, recipe unit, pantry kcal_per_100, pantry unit."""
    if not dish_ids:
        return {}
    rows = (
        await session.execute(
            select(
                DishIngredient.dish_id,
                Ingredient.name,
                DishIngredient.quantity,
                DishIngredient.unit,
                Ingredient.kcal_per_100,
                Ingredient.unit,
            )
            .join(Ingredient, Ingredient.id == DishIngredient.ingredient_id)
            .where(DishIngredient.dish_id.in_(dish_ids))
            .order_by(DishIngredient.sort_order, Ingredient.name)
        )
    ).all()
    out: dict[uuid.UUID, list[tuple[str, float, str, float | None, str]]] = {did: [] for did in dish_ids}
    for dish_id, name, qty, unit, kcal_per_100, pantry_unit in rows:
        kcal = float(kcal_per_100) if kcal_per_100 is not None else None
        out.setdefault(dish_id, []).append((name, float(qty), unit, kcal, pantry_unit or unit))
    return out


def _health_lines_for_score(rows: list[tuple[str, float, str, float | None, str]]) -> list[tuple[str, float, str]]:
    return [(name, qty, unit) for name, qty, unit, _kcal, _iunit in rows]


async def snapshots_for_dishes(
    session: AsyncSession,
    dishes: list[Dish],
) -> dict[uuid.UUID, DishHealthSnapshot]:
    from app.dish_calories import (
        apply_public_calorie_flags,
        is_healthy_tag,
        line_kcal,
        sum_recipe_kcal,
    )
    from ckac_common.platform_config import (
        DISH_CALORIES_FLAG,
        DISH_HEALTHY_TAG_FLAG,
        get_healthy_food_params,
        is_feature_enabled,
    )

    calories_on = await is_feature_enabled(session, DISH_CALORIES_FLAG, default=True)
    healthy_on = await is_feature_enabled(session, DISH_HEALTHY_TAG_FLAG, default=True)
    max_kcal, min_score = await get_healthy_food_params(session)

    lines_by_dish = await load_recipe_lines(session, [d.id for d in dishes])
    out: dict[uuid.UUID, DishHealthSnapshot] = {}
    for dish in dishes:
        rows = lines_by_dish.get(dish.id, [])
        snap = score_ingredient_lines(_health_lines_for_score(rows))
        kcal_total, _mapped, n, complete = sum_recipe_kcal(
            [(kcal, qty, unit, iunit) for _name, qty, unit, kcal, iunit in rows]
        )
        kcal_by_profile: dict[str, float] = {}
        for name, qty, unit, kcal_per_100, iunit in rows:
            line = line_kcal(
                kcal_per_100=kcal_per_100,
                quantity=qty,
                recipe_unit=unit,
                ingredient_unit=iunit,
            )
            if line is None:
                continue
            profile = lookup_health_profile(name)
            key = profile.name if profile else name
            kcal_by_profile[key] = round(kcal_by_profile.get(key, 0.0) + line, 1)
        ingredients = [
            ing.model_copy(update={"kcal": kcal_by_profile.get(ing.name)})
            for ing in snap.ingredients
        ]
        seen = {ing.name.lower() for ing in ingredients}
        for name, qty, unit, kcal_per_100, iunit in rows:
            profile = lookup_health_profile(name)
            key = (profile.name if profile else name).lower()
            if key in seen:
                continue
            extras_kcal = line_kcal(
                kcal_per_100=kcal_per_100,
                quantity=qty,
                recipe_unit=unit,
                ingredient_unit=iunit,
            )
            ingredients.append(
                IngredientHealthLine(
                    name=name,
                    score=0,
                    benefits="Not in the health library — kcal is the pantry estimate.",
                    disadvantages="",
                    quantity=qty,
                    unit=unit,
                    kcal=extras_kcal,
                )
            )
            seen.add(key)
        note = (getattr(dish, "calories_description", None) or None)
        tag = is_healthy_tag(
            calories_kcal=kcal_total,
            complete=complete,
            health_score=snap.score,
            recipe_lines=n,
            max_kcal=max_kcal,
            min_score=min_score,
        )
        pub_kcal, pub_note, pub_incomplete, pub_tag = apply_public_calorie_flags(
            calories_kcal=kcal_total,
            calories_description=note,
            calories_incomplete=(n > 0 and not complete),
            healthy_tag=tag,
            calories_enabled=calories_on,
            healthy_tag_enabled=healthy_on,
        )
        if not calories_on:
            ingredients = [ing.model_copy(update={"kcal": None}) for ing in ingredients]
        out[dish.id] = snap.model_copy(
            update={
                "dish_id": dish.id,
                "dish_name": dish.name,
                "kitchen_id": dish.kitchen_id,
                "ingredients": ingredients,
                "calories_kcal": pub_kcal,
                "calories_description": pub_note,
                "calories_incomplete": pub_incomplete,
                "healthy_tag": pub_tag,
            }
        )
    return out


async def health_enabled(session: AsyncSession) -> bool:
    try:
        return await is_feature_enabled(session, HEALTH_FEATURE, default=True)
    except Exception:
        return True
