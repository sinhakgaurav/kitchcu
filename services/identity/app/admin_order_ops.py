"""Admin kitchen order CSV + parse-stats (identity cross-schema read of ckac_orders).

Column set must stay aligned with `services/order/app/exports.py`.
"""

from __future__ import annotations

import csv
import io
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

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


def render_orders_csv(rows: list[dict[str, Any]]) -> bytes:
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf, fieldnames=CSV_HEADERS, extrasaction="ignore", lineterminator="\n"
    )
    writer.writeheader()
    for row in rows:
        writer.writerow({key: "" if row.get(key) is None else row[key] for key in CSV_HEADERS})
    return buf.getvalue().encode("utf-8-sig")


async def kitchen_exists(session: AsyncSession, kitchen_id: uuid.UUID) -> bool:
    row = (
        await session.execute(
            text("SELECT 1 FROM ckac_identity.kitchens WHERE id = :kid LIMIT 1"),
            {"kid": kitchen_id},
        )
    ).scalar_one_or_none()
    return row is not None


async def export_admin_kitchen_orders_csv(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
) -> bytes:
    result = await session.execute(
        text(
            """
            SELECT
                o.order_code,
                o.created_at,
                o.status,
                o.source,
                o.customer_name,
                o.customer_phone,
                o.subtotal,
                o.delivery_fee,
                COALESCE(o.discount_amount, 0) AS discount_amount,
                o.total,
                o.payment_method,
                o.delivery_type,
                COALESCE(
                    string_agg(oi.quantity::text || 'x ' || oi.dish_name, '; ' ORDER BY oi.id),
                    ''
                ) AS items
            FROM ckac_orders.orders o
            LEFT JOIN ckac_orders.order_items oi ON oi.order_id = o.id
            WHERE o.kitchen_id = :kid
            GROUP BY o.id
            ORDER BY o.created_at DESC
            LIMIT :lim
            """
        ),
        {"kid": kitchen_id, "lim": EXPORT_MAX_ROWS + 1},
    )
    mappings = list(result.mappings().all())
    if len(mappings) > EXPORT_MAX_ROWS:
        raise ValueError(
            f"Export is capped at {EXPORT_MAX_ROWS} orders. Narrow the date range and try again."
        )
    rows = []
    for row in mappings:
        created = row["created_at"]
        rows.append(
            {
                "order_code": row["order_code"],
                "created_at": created.isoformat() if created else "",
                "status": row["status"],
                "source": row["source"],
                "customer_name": row["customer_name"] or "",
                "customer_phone": row["customer_phone"] or "",
                "items": row["items"] or "",
                "subtotal": f"{float(row['subtotal']):.2f}",
                "delivery_fee": f"{float(row['delivery_fee']):.2f}",
                "discount_amount": f"{float(row['discount_amount']):.2f}",
                "total": f"{float(row['total']):.2f}",
                "payment_method": row["payment_method"],
                "delivery_type": row["delivery_type"],
            }
        )
    return render_orders_csv(rows)


async def admin_kitchen_parse_stats(
    session: AsyncSession,
    kitchen_id: uuid.UUID,
    *,
    days: int = 30,
) -> dict[str, Any]:
    window_days = max(1, min(days, PARSE_STATS_MAX_DAYS))
    since = datetime.now(UTC) - timedelta(days=window_days)
    result = await session.execute(
        text(
            """
            SELECT parsed_items, unmatched_lines
            FROM ckac_orders.order_drafts
            WHERE kitchen_id = :kid AND created_at >= :since
            """
        ),
        {"kid": kitchen_id, "since": since},
    )
    lines_total = 0
    lines_matched = 0
    drafts_with_unmatched = 0
    drafts = 0
    for row in result.mappings().all():
        drafts += 1
        items = row["parsed_items"] or []
        unmatched = row["unmatched_lines"] or []
        n = len(items)
        m = sum(1 for item in items if item.get("matched"))
        lines_total += n
        lines_matched += m
        if unmatched or any(not item.get("matched") for item in items):
            drafts_with_unmatched += 1
    match_rate = round(lines_matched / lines_total, 4) if lines_total else None
    return {
        "kitchen_id": kitchen_id,
        "days": window_days,
        "drafts": drafts,
        "lines_total": lines_total,
        "lines_matched": lines_matched,
        "match_rate": match_rate,
        "drafts_with_unmatched": drafts_with_unmatched,
    }
