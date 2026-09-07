"""First-party order CSV + WhatsApp parse match-rate (F05 / F01). Stdlib only."""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

CSV_HEADERS = [
    "order_code",
    "created_at",
    "status",
    "source",
    "customer_name",
    "customer_phone",
    "items",
    "subtotal",
    "delivery_fee",
    "discount_amount",
    "total",
    "payment_method",
    "delivery_type",
]

EXPORT_MAX_ROWS = 10_000
PARSE_STATS_MAX_DAYS = 90
PARSE_STATS_DEFAULT_DAYS = 30


def format_order_items(items: Sequence[Mapping[str, Any]] | None) -> str:
    parts: list[str] = []
    for item in items or []:
        qty = item.get("quantity", 1)
        name = item.get("dish_name") or ""
        parts.append(f"{qty}x {name}".strip())
    return "; ".join(parts)


def render_orders_csv(rows: Iterable[Mapping[str, Any]]) -> bytes:
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=CSV_HEADERS,
        extrasaction="ignore",
        lineterminator="\n",
    )
    writer.writeheader()
    for row in rows:
        writer.writerow({key: "" if row.get(key) is None else row[key] for key in CSV_HEADERS})
    return buf.getvalue().encode("utf-8-sig")


def compute_parse_stats(
    drafts: Iterable[Mapping[str, Any]],
    *,
    days: int,
) -> dict[str, Any]:
    """Match rate = matched parsed lines / all parsed lines in the window."""
    drafts_list = list(drafts)
    lines_total = 0
    lines_matched = 0
    drafts_with_unmatched = 0
    for draft in drafts_list:
        items = draft.get("parsed_items") or []
        unmatched = draft.get("unmatched_lines") or []
        n = len(items)
        m = sum(1 for item in items if item.get("matched"))
        lines_total += n
        lines_matched += m
        has_unmatched = bool(unmatched) or any(not item.get("matched") for item in items)
        if has_unmatched:
            drafts_with_unmatched += 1
    match_rate = round(lines_matched / lines_total, 4) if lines_total else None
    return {
        "days": days,
        "drafts": len(drafts_list),
        "lines_total": lines_total,
        "lines_matched": lines_matched,
        "match_rate": match_rate,
        "drafts_with_unmatched": drafts_with_unmatched,
    }
