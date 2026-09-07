"""F01 parse match-rate from stored drafts (no Meta)."""

import json
import uuid
from datetime import UTC, datetime, timedelta

import psycopg2
import pytest
from httpx import AsyncClient

from tests.conftest import SYNC_DB_URL


def _insert_draft(
    kitchen_id: uuid.UUID,
    *,
    parsed_items: list[dict],
    unmatched_lines: list[str],
    created_at: datetime | None = None,
    status: str = "draft",
) -> uuid.UUID:
    draft_id = uuid.uuid4()
    when = created_at or datetime.now(UTC)
    conn = psycopg2.connect(SYNC_DB_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ckac_orders.order_drafts
                (id, kitchen_id, status, source, raw_message, parsed_items,
                 unmatched_lines, special_notes, created_at, updated_at)
            VALUES (
                %s::uuid, %s::uuid, %s, 'whatsapp', 'test msg',
                %s::jsonb, %s::jsonb, '[]'::jsonb, %s, %s
            )
            """,
            (
                str(draft_id),
                str(kitchen_id),
                status,
                json.dumps(parsed_items),
                json.dumps(unmatched_lines),
                when,
                when,
            ),
        )
    conn.close()
    return draft_id


@pytest.mark.asyncio
async def test_parse_stats_requires_auth(client: AsyncClient, order_ctx):
    _, kitchen_id, _, _, _ = order_ctx
    response = await client.get(f"/api/v1/kitchens/{kitchen_id}/orders/drafts/parse-stats")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_parse_stats_match_rate_and_window(client: AsyncClient, order_ctx):
    _, kitchen_id, dish_id, _, token = order_ctx
    headers = {"Authorization": f"Bearer {token}"}
    now = datetime.now(UTC)
    _insert_draft(
        kitchen_id,
        parsed_items=[
            {"raw": "2 paneer", "dish_id": str(dish_id), "dish_name": "Paneer Tikka", "quantity": 2, "matched": True},
            {"raw": "mystery", "dish_id": None, "dish_name": None, "quantity": 1, "matched": False},
        ],
        unmatched_lines=["mystery"],
    )
    _insert_draft(
        kitchen_id,
        parsed_items=[
            {"raw": "1 naan", "dish_id": str(dish_id), "dish_name": "Paneer Tikka", "quantity": 1, "matched": True},
        ],
        unmatched_lines=[],
        status="confirmed",
    )
    _insert_draft(
        kitchen_id,
        parsed_items=[{"raw": "old", "matched": False, "quantity": 1}],
        unmatched_lines=["old"],
        created_at=now - timedelta(days=40),
    )

    response = await client.get(
        f"/api/v1/kitchens/{kitchen_id}/orders/drafts/parse-stats",
        params={"days": 30},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["days"] == 30
    assert data["drafts"] == 2
    assert data["lines_total"] == 3
    assert data["lines_matched"] == 2
    assert data["match_rate"] == 0.6667
    assert data["drafts_with_unmatched"] == 1


@pytest.mark.asyncio
async def test_parse_stats_isolated_by_kitchen(client: AsyncClient, order_ctx):
    from tests.conftest import _seed_kitchen_with_dish

    _, kitchen_id, _, _, token = order_ctx
    _insert_draft(
        kitchen_id,
        parsed_items=[{"matched": True, "quantity": 1}],
        unmatched_lines=[],
    )
    _, other_kitchen, _, _, _ = _seed_kitchen_with_dish()
    _insert_draft(
        other_kitchen,
        parsed_items=[{"matched": False, "quantity": 1}],
        unmatched_lines=["x"],
    )
    response = await client.get(
        f"/api/v1/kitchens/{kitchen_id}/orders/drafts/parse-stats",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["drafts"] == 1
    assert data["lines_matched"] == 1
    assert data["drafts_with_unmatched"] == 0
