"""Optional LLM order parser — gated by ``order_parser_llm`` feature flag."""

from __future__ import annotations

import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.parser import ParseResult, ParsedLine, match_dishes, parse_message_text
from ckac_common.platform_config import get_platform_secret, is_feature_enabled

logger = logging.getLogger(__name__)


async def parse_order_message(
    session: AsyncSession,
    message_text: str,
    menu: list[dict],
) -> ParseResult:
    """Parse WhatsApp order text — LLM when enabled, else rule-based."""
    if await is_feature_enabled(session, "order_parser_llm", default=False):
        try:
            llm_result = await _try_llm_parse(session, message_text, menu)
            if llm_result is not None:
                return llm_result
        except Exception as exc:
            logger.warning("LLM order parser failed, using rules: %s", exc)
    parsed = parse_message_text(message_text)
    return match_dishes(parsed, menu)


async def _try_llm_parse(
    session: AsyncSession,
    message_text: str,
    menu: list[dict],
) -> ParseResult | None:
    api_key = await get_platform_secret(session, "support_ai_api_key")
    if not api_key:
        return None

    dish_names = [d.get("name", "") for d in menu[:40]]
    prompt = (
        "Extract food order lines as JSON array: "
        '[{"dish_name":"...","quantity":1}]. '
        f"Known dishes: {', '.join(dish_names)}. "
        f"Message:\n{message_text}"
    )

    import httpx

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
            },
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]

    start = content.find("[")
    end = content.rfind("]")
    if start < 0 or end <= start:
        return None
    items = json.loads(content[start : end + 1])
    lines = [
        ParsedLine(raw=str(it.get("dish_name", "")), dish_name=str(it.get("dish_name", "")), quantity=int(it.get("quantity", 1)))
        for it in items
        if it.get("dish_name")
    ]
    if not lines:
        return None
    return match_dishes(ParseResult(lines=lines), menu)
