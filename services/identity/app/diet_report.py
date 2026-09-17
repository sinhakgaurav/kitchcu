"""Checkup-report ML parser + dish compatibility (customer diet filter).

In-process multi-label logistic models (no sklearn) trained on embedded lab/report
snippets, plus conservative lab-value thresholds. Output is a kitchen discovery
filter — not a diagnosis.
"""

from __future__ import annotations

import io
import math
import re
import uuid
from dataclasses import dataclass, field
from functools import lru_cache

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

DIET_FEATURE = "customer_diet_report"
DISCLAIMER = (
    "This is a kitchen discovery filter from your report text, not a diagnosis "
    "or treatment plan. Confirm with your clinician."
)

CONDITION_IDS = (
    "diabetes",
    "hypertension",
    "ckd",
    "gout",
    "hyperlipidemia",
    "hypothyroidism",
    "celiac",
    "lactose_intolerance",
)

_CONDITION_KEYWORDS: dict[str, frozenset[str]] = {
    "diabetes": frozenset(
        {
            "diabetes",
            "diabetic",
            "mellitus",
            "hyperglycemia",
            "hba1c",
            "sugar",
            "insulin",
            "t2dm",
            "niddm",
        }
    ),
    "hypertension": frozenset(
        {
            "hypertension",
            "hypertensive",
            "bp",
            "systolic",
        }
    ),
    "ckd": frozenset(
        {
            "ckd",
            "creatinine",
            "nephropathy",
            "kidney",
            "renal",
            "egfr",
        }
    ),
    "gout": frozenset({"gout", "uric", "hyperuricemia", "urate"}),
    "hyperlipidemia": frozenset(
        {
            "cholesterol",
            "ldl",
            "triglyceride",
            "lipid",
            "dyslipidemia",
            "hyperlipidemia",
        }
    ),
    "hypothyroidism": frozenset({"thyroid", "tsh", "hypothyroid", "hypothyroidism"}),
    "celiac": frozenset({"celiac", "coeliac", "gluten", "ttg"}),
    "lactose_intolerance": frozenset({"lactose", "lactase", "dairy intolerance"}),
}

_CONDITION_RULES: dict[str, dict[str, tuple[str, ...]]] = {
    "diabetes": {
        "avoid_categories": ("desserts",),
        "avoid_ingredients": ("sugar", "jaggery", "honey", "glucose"),
        "avoid_name_tokens": (
            "gulab",
            "jamun",
            "rasgulla",
            "jalebi",
            "kheer",
            "payasam",
            "halwa",
            "ladoo",
            "laddu",
            "barfi",
            "rasmalai",
            "cola",
            "soda",
            "sweet",
        ),
        "prefer_categories": ("veg", "vegan"),
    },
    "hypertension": {
        "avoid_categories": (),
        "avoid_ingredients": ("salt",),
        "avoid_name_tokens": ("pickle", "achar", "papad", "namkeen", "chips"),
        "prefer_categories": ("veg",),
    },
    "ckd": {
        "avoid_categories": (),
        "avoid_ingredients": ("salt",),
        "avoid_name_tokens": ("pickle", "papad", "namkeen"),
        "prefer_categories": ("veg",),
    },
    "gout": {
        "avoid_categories": (),
        "avoid_ingredients": (),
        "avoid_name_tokens": ("mutton", "organ", "liver", "kidney", "red meat"),
        "prefer_categories": ("veg",),
    },
    "hyperlipidemia": {
        "avoid_categories": ("desserts",),
        "avoid_ingredients": ("cream", "malai", "butter"),
        "avoid_name_tokens": ("fried", "pakora", "pakoda", "poori", "puri", "samosa"),
        "prefer_categories": ("veg",),
    },
    "hypothyroidism": {
        "avoid_categories": (),
        "avoid_ingredients": (),
        "avoid_name_tokens": ("soy", "soya"),
        "prefer_categories": (),
    },
    "celiac": {
        "avoid_categories": (),
        "avoid_ingredients": ("wheat", "maida", "atta"),
        "avoid_name_tokens": (
            "roti",
            "naan",
            "paratha",
            "poori",
            "puri",
            "samosa",
            "bread",
            "pasta",
            "maida",
        ),
        "prefer_categories": (),
    },
    "lactose_intolerance": {
        "avoid_categories": (),
        "avoid_ingredients": ("milk", "paneer", "cream", "dahi", "curd", "cheese"),
        "avoid_name_tokens": ("paneer", "lassi", "raita", "kheer", "milk", "dahi"),
        "prefer_categories": ("vegan",),
    },
}

_SUMMARIES = {
    "diabetes": "Elevated sugar markers — prefer lower-sugar home plates.",
    "hypertension": "Blood-pressure flags — prefer lower-salt home plates.",
    "ckd": "Kidney markers — prefer lower-salt home plates.",
    "gout": "Uric-acid flags — skip organ meat and heavy mutton plates.",
    "hyperlipidemia": "Lipid flags — prefer less fried and dessert-heavy plates.",
    "hypothyroidism": "Thyroid markers — keep soy-heavy plates off the default list.",
    "celiac": "Gluten flags — skip wheat/maida rotis and fried maida snacks.",
    "lactose_intolerance": "Lactose flags — skip milk, paneer, and curd-heavy plates.",
}

# (report snippet, labels) — fit one-vs-rest logistics at import.
_TRAINING_EXAMPLES: list[tuple[str, frozenset[str]]] = [
    ("HbA1c 8.2% Type 2 Diabetes Mellitus fasting glucose 168 mg/dl", frozenset({"diabetes"})),
    ("Known T2DM on insulin. Hyperglycemia. Sugar high.", frozenset({"diabetes"})),
    ("Random blood sugar 210 diabetic nephropathy follow up", frozenset({"diabetes", "ckd"})),
    ("Blood pressure 168/102 mmHg essential hypertension", frozenset({"hypertension"})),
    ("Hypertensive urgency systolic 180 on amlodipine", frozenset({"hypertension"})),
    ("Serum creatinine 2.4 mg/dl CKD stage 3 eGFR 28", frozenset({"ckd"})),
    ("Chronic kidney disease renal clinic creatinine 1.9", frozenset({"ckd"})),
    ("Uric acid 9.1 mg/dl acute gout flare", frozenset({"gout"})),
    ("Hyperuricemia urate high advice low purine diet", frozenset({"gout"})),
    ("LDL 188 mg/dl total cholesterol 260 dyslipidemia", frozenset({"hyperlipidemia"})),
    ("Lipid profile triglycerides 320 hyperlipidemia", frozenset({"hyperlipidemia"})),
    ("TSH 18.4 mIU/L hypothyroidism on thyroxine", frozenset({"hypothyroidism"})),
    ("Thyroid function hypothyroid TSH elevated", frozenset({"hypothyroidism"})),
    ("tTG IgA positive coeliac disease gluten free diet", frozenset({"celiac"})),
    ("Celiac serology strongly positive avoid wheat", frozenset({"celiac"})),
    ("Lactose intolerance hydrogen breath test positive", frozenset({"lactose_intolerance"})),
    ("Lactase deficiency avoid dairy milk paneer", frozenset({"lactose_intolerance"})),
    ("Complete blood count within normal limits Hb 13.2", frozenset()),
    ("Vitamin D insufficient otherwise healthy adult", frozenset()),
    ("Annual wellness visit no chronic illness recorded", frozenset()),
    ("HbA1c 5.2% fasting glucose 88 mg/dl normal", frozenset()),
    ("BP 118/76 mmHg cholesterol 165 LDL 92", frozenset()),
]

_TOKEN_RE = re.compile(r"[a-zA-Z]+")
_HBA1C_RE = re.compile(r"hba1c[^0-9%]{0,16}(\d+(?:\.\d+)?)\s*%?", re.I)
_GLUCOSE_RE = re.compile(
    r"(?:fasting|fbs|fbg|blood sugar|glucose)[^0-9]{0,24}(\d{2,3})",
    re.I,
)
_BP_RE = re.compile(
    r"(?:bp|blood pressure)[^0-9]{0,20}(\d{2,3})\s*/\s*(\d{2,3})",
    re.I,
)
_CREAT_RE = re.compile(r"creatinine[^0-9]{0,16}(\d+(?:\.\d+)?)", re.I)
_LDL_RE = re.compile(r"\bldl\b[^0-9]{0,16}(\d{2,3})", re.I)
_URIC_RE = re.compile(r"uric acid[^0-9]{0,16}(\d+(?:\.\d+)?)", re.I)
_TSH_RE = re.compile(r"\btsh\b[^0-9]{0,16}(\d+(?:\.\d+)?)", re.I)

MAX_REPORT_BYTES = 8 * 1024 * 1024
MAX_NOTES_CHARS = 4000


@dataclass(frozen=True)
class DietProfile:
    conditions: list[str]
    avoid_ingredients: list[str]
    avoid_categories: list[str]
    avoid_name_tokens: list[str]
    prefer_categories: list[str] = field(default_factory=list)
    confidence: float = 0.0
    summary: str = ""
    disclaimer: str = DISCLAIMER

    def to_dict(self) -> dict:
        return {
            "conditions": list(self.conditions),
            "avoid_ingredients": list(self.avoid_ingredients),
            "avoid_categories": list(self.avoid_categories),
            "avoid_name_tokens": list(self.avoid_name_tokens),
            "prefer_categories": list(self.prefer_categories),
            "confidence": self.confidence,
            "summary": self.summary,
            "disclaimer": self.disclaimer,
        }


def profile_from_dict(raw: object) -> DietProfile | None:
    if not isinstance(raw, dict):
        return None
    conditions = [c for c in raw.get("conditions") or [] if c in CONDITION_IDS]
    return DietProfile(
        conditions=conditions,
        avoid_ingredients=[str(x).lower() for x in (raw.get("avoid_ingredients") or []) if x],
        avoid_categories=[str(x).lower() for x in (raw.get("avoid_categories") or []) if x],
        avoid_name_tokens=[str(x).lower() for x in (raw.get("avoid_name_tokens") or []) if x],
        prefer_categories=[str(x).lower() for x in (raw.get("prefer_categories") or []) if x],
        confidence=float(raw.get("confidence") or 0.0),
        summary=str(raw.get("summary") or ""),
        disclaimer=str(raw.get("disclaimer") or DISCLAIMER),
    )


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "")]


def extract_lab_values(text: str) -> dict[str, float]:
    blob = text or ""
    out: dict[str, float] = {}
    if m := _HBA1C_RE.search(blob):
        out["hba1c"] = float(m.group(1))
    if m := _GLUCOSE_RE.search(blob):
        out["glucose"] = float(m.group(1))
    if m := _BP_RE.search(blob):
        out["systolic"] = float(m.group(1))
        out["diastolic"] = float(m.group(2))
    if m := _CREAT_RE.search(blob):
        out["creatinine"] = float(m.group(1))
    if m := _LDL_RE.search(blob):
        out["ldl"] = float(m.group(1))
    if m := _URIC_RE.search(blob):
        out["uric_acid"] = float(m.group(1))
    if m := _TSH_RE.search(blob):
        out["tsh"] = float(m.group(1))
    return out


def extract_features(text: str) -> list[float]:
    tokens = _tokenize(text)
    n = max(len(tokens), 1)
    token_set = set(tokens)
    labs = extract_lab_values(text)
    keyword_hits = []
    for cid in CONDITION_IDS:
        hits = sum(1 for k in _CONDITION_KEYWORDS[cid] if k in token_set or k in (text or "").lower())
        keyword_hits.append(hits / n)
    return [
        1.0,
        *keyword_hits,
        min(labs.get("hba1c", 0.0) / 12.0, 1.0),
        min(labs.get("glucose", 0.0) / 250.0, 1.0),
        min(labs.get("systolic", 0.0) / 200.0, 1.0),
        min(labs.get("creatinine", 0.0) / 5.0, 1.0),
        min(labs.get("ldl", 0.0) / 250.0, 1.0),
        min(labs.get("uric_acid", 0.0) / 12.0, 1.0),
        min(labs.get("tsh", 0.0) / 20.0, 1.0),
    ]


def _sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


class ConditionLogit:
    """One-vs-rest logistic trained on embedded checkup snippets."""

    def __init__(self, condition: str, weights: list[float] | None = None) -> None:
        self.condition = condition
        dim = len(extract_features(""))
        self.weights = list(weights) if weights is not None else [0.0] * dim
        if weights is None:
            self._fit()

    def _fit(self, lr: float = 0.4, epochs: int = 450) -> None:
        xs = [extract_features(t) for t, _ in _TRAINING_EXAMPLES]
        ys = [1.0 if self.condition in labels else 0.0 for _, labels in _TRAINING_EXAMPLES]
        w = self.weights
        n = len(xs)
        for _ in range(epochs):
            grads = [0.0] * len(w)
            for x, y in zip(xs, ys, strict=True):
                pred = _sigmoid(sum(wi * xi for wi, xi in zip(w, x, strict=True)))
                err = pred - y
                for i in range(len(w)):
                    grads[i] += err * x[i]
            for i in range(len(w)):
                w[i] -= lr * (grads[i] / n)
        self.weights = w

    def predict_proba(self, text: str) -> float:
        x = extract_features(text)
        return _sigmoid(sum(wi * xi for wi, xi in zip(self.weights, x, strict=True)))


@lru_cache(maxsize=1)
def _models() -> dict[str, ConditionLogit]:
    return {cid: ConditionLogit(cid) for cid in CONDITION_IDS}


def lab_condition_overrides(text: str) -> set[str]:
    """Conservative screening thresholds — still not a diagnosis."""
    labs = extract_lab_values(text)
    found: set[str] = set()
    blob = (text or "").lower()
    if labs.get("hba1c", 0) >= 6.5 or labs.get("glucose", 0) >= 126:
        found.add("diabetes")
    if labs.get("systolic", 0) >= 140 or labs.get("diastolic", 0) >= 90:
        found.add("hypertension")
    if labs.get("creatinine", 0) >= 1.5:
        found.add("ckd")
    if labs.get("uric_acid", 0) >= 7.0:
        found.add("gout")
    if labs.get("ldl", 0) >= 160:
        found.add("hyperlipidemia")
    if labs.get("tsh", 0) >= 10.0:
        found.add("hypothyroidism")
    if "celiac" in blob or "coeliac" in blob or "gluten" in blob:
        found.add("celiac")
    if "lactose" in blob:
        found.add("lactose_intolerance")
    if "diabetes" in blob or "diabetic" in blob or "t2dm" in blob:
        found.add("diabetes")
    if "hypertension" in blob:
        found.add("hypertension")
    if " gout" in f" {blob}" or blob.startswith("gout"):
        found.add("gout")
    return found


def parse_report_to_profile(text: str) -> DietProfile:
    blob = (text or "").strip()
    models = _models()
    scores = {cid: models[cid].predict_proba(blob) for cid in CONDITION_IDS}
    ml_hits = {cid for cid, p in scores.items() if p >= 0.55}
    hits = sorted(ml_hits | lab_condition_overrides(blob))
    avoid_ing: list[str] = []
    avoid_cat: list[str] = []
    avoid_tok: list[str] = []
    prefer: list[str] = []
    for cid in hits:
        rules = _CONDITION_RULES[cid]
        avoid_ing.extend(rules["avoid_ingredients"])
        avoid_cat.extend(rules["avoid_categories"])
        avoid_tok.extend(rules["avoid_name_tokens"])
        prefer.extend(rules["prefer_categories"])

    def _uniq(items: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for item in items:
            key = item.lower().strip()
            if key and key not in seen:
                seen.add(key)
                out.append(key)
        return out

    confidence = round(max((scores[c] for c in hits), default=0.35), 4) if hits else 0.2
    if hits:
        summary = " ".join(_SUMMARIES[c] for c in hits)
    else:
        summary = "No diet flags were clear from this report. You can still browse every kitchen."
    return DietProfile(
        conditions=hits,
        avoid_ingredients=_uniq(avoid_ing),
        avoid_categories=_uniq(avoid_cat),
        avoid_name_tokens=_uniq(avoid_tok),
        prefer_categories=_uniq(prefer),
        confidence=confidence,
        summary=summary,
        disclaimer=DISCLAIMER,
    )


def extract_pdf_text(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    parts: list[str] = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts).strip()


def extract_report_text(*, data: bytes, notes: str | None) -> str:
    notes_clean = (notes or "").strip()[:MAX_NOTES_CHARS]
    extracted = ""
    if data.startswith(b"%PDF"):
        try:
            extracted = extract_pdf_text(data)
        except Exception:
            extracted = ""
    # Images have no local OCR; notes (or a text PDF) carry the parseable content.
    combined = "\n".join(part for part in (extracted, notes_clean) if part).strip()
    return combined


def sniff_checkup_file(data: bytes) -> tuple[str, str]:
    from app.customer_media import sniff_image
    from fastapi import HTTPException, status

    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
    if len(data) > MAX_REPORT_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File exceeds 8MB")
    if data.startswith(b"%PDF"):
        return "application/pdf", "pdf"
    return sniff_image(data)


def upload_checkup_file(*, customer_id: uuid.UUID, data: bytes) -> str:
    from ckac_common.storage import get_media_storage

    content_type, ext = sniff_checkup_file(data)
    return get_media_storage().upload(
        kitchen_id=f"customer-{customer_id}",
        context="checkup-report",
        data=data,
        content_type=content_type,
        extension=ext,
    )


def _haystack(*parts: str) -> str:
    blob = re.sub(r"[^a-z0-9]+", " ", " ".join(p or "" for p in parts).lower())
    return f" {blob.strip()} "


def _token_in(hay: str, token: str) -> bool:
    tok = re.sub(r"[^a-z0-9]+", " ", (token or "").lower()).strip()
    if not tok:
        return False
    return f" {tok} " in hay


def dish_is_compatible(
    *,
    name: str,
    category_slug: str,
    ingredient_blob: str,
    profile: DietProfile,
) -> bool:
    slug = (category_slug or "").lower().strip()
    if slug and slug in {c.lower() for c in profile.avoid_categories}:
        return False
    hay = _haystack(name, slug.replace("_", " "), ingredient_blob)
    for tok in profile.avoid_name_tokens:
        if _token_in(hay, tok):
            return False
    for ing in profile.avoid_ingredients:
        if _token_in(hay, ing):
            return False
    return True


@dataclass(frozen=True)
class KitchenDishRow:
    kitchen_id: uuid.UUID
    dish_id: uuid.UUID
    name: str
    category_slug: str
    ingredient_blob: str


async def load_kitchen_dishes(
    session: AsyncSession,
    kitchen_ids: list[uuid.UUID],
) -> list[KitchenDishRow]:
    if not kitchen_ids:
        return []
    stmt = text(
        """
        SELECT
            d.kitchen_id,
            d.id AS dish_id,
            d.name,
            COALESCE(c.slug, '') AS category_slug,
            CONCAT_WS(
                ' ',
                COALESCE(d.ingredients_description, ''),
                COALESCE(string_agg(i.name, ' '), '')
            ) AS ingredient_blob
        FROM ckac_catalog.dishes d
        LEFT JOIN ckac_catalog.categories c ON c.id = d.category_id
        LEFT JOIN ckac_catalog.dish_ingredients di ON di.dish_id = d.id
        LEFT JOIN ckac_catalog.ingredients i ON i.id = di.ingredient_id
        WHERE d.is_active = true
          AND d.kitchen_id IN :kitchen_ids
        GROUP BY d.kitchen_id, d.id, c.slug
        """
    ).bindparams(bindparam("kitchen_ids", expanding=True))
    result = await session.execute(stmt, {"kitchen_ids": kitchen_ids})
    rows: list[KitchenDishRow] = []
    for row in result.all():
        rows.append(
            KitchenDishRow(
                kitchen_id=row.kitchen_id,
                dish_id=row.dish_id,
                name=row.name,
                category_slug=row.category_slug or "",
                ingredient_blob=row.ingredient_blob or "",
            )
        )
    return rows


def compatible_counts(
    rows: list[KitchenDishRow],
    profile: DietProfile,
) -> dict[uuid.UUID, tuple[int, int]]:
    totals: dict[uuid.UUID, int] = {}
    ok: dict[uuid.UUID, int] = {}
    for row in rows:
        totals[row.kitchen_id] = totals.get(row.kitchen_id, 0) + 1
        if dish_is_compatible(
            name=row.name,
            category_slug=row.category_slug,
            ingredient_blob=row.ingredient_blob,
            profile=profile,
        ):
            ok[row.kitchen_id] = ok.get(row.kitchen_id, 0) + 1
    return {kid: (ok.get(kid, 0), totals.get(kid, 0)) for kid in totals}


def compatible_dish_ids_for_kitchen(
    rows: list[KitchenDishRow],
    profile: DietProfile,
    kitchen_id: uuid.UUID,
) -> list[uuid.UUID]:
    ids: list[uuid.UUID] = []
    for row in rows:
        if row.kitchen_id != kitchen_id:
            continue
        if dish_is_compatible(
            name=row.name,
            category_slug=row.category_slug,
            ingredient_blob=row.ingredient_blob,
            profile=profile,
        ):
            ids.append(row.dish_id)
    return ids


async def active_diet_profile(session: AsyncSession, customer: object | None) -> DietProfile | None:
    """Return a parse profile only when the diner opted in and the kill-switch is on."""
    if customer is None or not getattr(customer, "diet_filter_enabled", False):
        return None
    from ckac_common.platform_config import is_feature_enabled

    if not await is_feature_enabled(session, DIET_FEATURE, default=True):
        return None
    return profile_from_dict(getattr(customer, "diet_profile", None))


def rank_kitchens_for_diet(
    kitchens: list,
    counts: dict[uuid.UUID, tuple[int, int]],
    *,
    limit: int,
) -> list:
    """Drop kitchens with zero compatible dishes; best match first, then nearer."""
    scored = []
    for kitchen in kitchens:
        n, _total = counts.get(kitchen.id, (0, 0))
        if n <= 0:
            continue
        kitchen.compatible_dish_count = n
        scored.append(kitchen)
    scored.sort(key=lambda k: (-(k.compatible_dish_count or 0), float(k.distance_km)))
    scored = scored[:limit]
    if scored:
        top = max(k.compatible_dish_count or 0 for k in scored)
        for kitchen in scored:
            kitchen.better_for_report = (kitchen.compatible_dish_count or 0) == top
    return scored


async def apply_diet_to_kitchens(
    session: AsyncSession,
    kitchens: list,
    profile: DietProfile | None,
    *,
    limit: int,
) -> list:
    if not profile or not kitchens:
        return kitchens
    rows = await load_kitchen_dishes(session, [k.id for k in kitchens])
    return rank_kitchens_for_diet(kitchens, compatible_counts(rows, profile), limit=limit)
