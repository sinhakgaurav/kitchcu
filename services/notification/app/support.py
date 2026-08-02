"""kitchCU support assistant — options-first, FAQ-grounded help.

Primary brain: ``packages/ai-context`` (FAQ answer_ids + main menus).
Optional OpenAI augmentation when SUPPORT_AI_API_KEY is set — always grounded
on matched FAQ / product facts so we never invent POS or food commission.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field

Audience = Literal["owner", "customer"]


def _ai_context_root() -> Path | None:
    env = os.environ.get("AI_CONTEXT_ROOT", "").strip()
    candidates = [
        Path(env) if env else None,
        Path("/app/packages/ai-context"),
        Path(__file__).resolve().parents[3] / "packages" / "ai-context",
        Path(__file__).resolve().parents[2] / "packages" / "ai-context",
    ]
    for root in candidates:
        if root and (root / "load.py").is_file():
            return root.resolve()
    return None


@lru_cache(maxsize=1)
def _pack() -> Any:
    root = _ai_context_root()
    if root is None:
        raise RuntimeError("ai-context pack not found — set AI_CONTEXT_ROOT")
    # load.py uses Path(__file__).parent — keep that; register module for dataclasses
    name = "ckac_ai_context_load"
    spec = importlib.util.spec_from_file_location(name, root / "load.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load ai-context pack")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


OWNER_GREETING = (
    "Hi! I'm the kitchCU owner assistant.\n\n"
    "I can help with pricing, WhatsApp orders, menus, delivery, billing/refunds, "
    "CRM, tiffin, and more. Pick a topic below or type a question."
)

CUSTOMER_GREETING = (
    "Hello! I'm the kitchCU customer assistant.\n\n"
    "I can help you find kitchens, checkout, track orders, payments, delivery fees, "
    "ratings, and tiffin plans. Pick a topic below or type a question."
)


class ChatMessage(BaseModel):
    """One turn in a support chat history."""

    role: Literal["user", "assistant"] = Field(..., description="Who sent this turn.")
    content: str = Field(..., min_length=1, max_length=2000, description="Message text.")


class SupportOption(BaseModel):
    id: str = Field(..., description="Option id to send back as selected_option_id or typed number.")
    label: str = Field(..., description="Button / chip label shown to the user.")


class SupportChatRequest(BaseModel):
    """Marketing-site AI support chat request."""

    audience: Audience = Field(
        ...,
        description="'owner' or 'customer' — selects the knowledge base and system prompt tone.",
    )
    message: str = Field(
        default="",
        max_length=2000,
        description="The user's latest message (optional when selected_option_id is set).",
    )
    selected_option_id: str | None = Field(
        default=None,
        max_length=8,
        description="Chip / menu option id from the previous turn.",
    )
    prior_options: list[SupportOption] = Field(
        default_factory=list,
        max_length=20,
        description="Options shown on the previous assistant turn (for number/label resolve).",
    )
    history: list[ChatMessage] = Field(
        default_factory=list,
        max_length=20,
        description="Prior turns in this conversation, oldest first (used for LLM context, last 8 kept).",
    )


class SupportChatResponse(BaseModel):
    """AI/knowledge-base support reply, with options and optional ticket prompt."""

    audience: Audience = Field(..., description="Echoes the request audience.")
    reply: str = Field(..., description="Assistant's reply text (markdown-formatted).")
    source: Literal["knowledge", "ai"] = Field(
        ...,
        description="'knowledge' — curated FAQ/menu. 'ai' — LLM-augmented grounded reply.",
    )
    answer_id: str | None = Field(default=None, description="Matched FAQ answer_id when available.")
    options: list[SupportOption] = Field(
        default_factory=list,
        description="Follow-up chips — options-first UX.",
    )
    suggest_ticket: bool = Field(
        default=False,
        description="True when escalation is recommended — UI should offer Raise ticket.",
    )
    suggested_category: str | None = Field(
        default=None,
        description="Pre-filled ticket category when suggest_ticket is true.",
    )


def knowledge_reply(audience: Audience, message: str) -> str:
    """Backward-compatible plain text reply (tests / legacy)."""
    pack = _pack()
    turn = pack.resolve_support_turn(audience, message)
    return turn.reply


async def _ai_reply(
    audience: Audience,
    message: str,
    history: list[ChatMessage],
    api_key: str,
    *,
    grounding: str,
    pack_reply: str,
) -> str | None:
    pack = _pack()
    prompt_name = "owner_support" if audience == "owner" else "customer_support"
    try:
        system = pack.system_prompt(prompt_name)
    except Exception:
        system = (
            "You are kitchCU support. Zero food commission. Not restaurants/POS. "
            "Be concise. Never invent features. Prefer the grounded FAQ below."
        )
    system = (
        f"{system}\n\n## Grounded FAQ (prefer these facts)\n{grounding}\n\n"
        f"## Preferred answer draft (keep meaning; you may polish tone)\n{pack_reply}\n\n"
        "If the draft answers the user, refine it slightly for warmth. "
        "Do not invent POS, dine-in, tables, waiters, or per-order food commission. "
        "End without inventing new option numbers — the UI adds chips separately."
    )
    messages = [{"role": "system", "content": system[:12000]}]
    for h in history[-8:]:
        messages.append({"role": h.role, "content": h.content})
    messages.append({"role": "user", "content": message or "(selected a menu option)"})

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": os.environ.get("SUPPORT_AI_MODEL", "gpt-4o-mini"),
                    "messages": messages,
                    "max_tokens": 450,
                    "temperature": 0.35,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


async def generate_support_reply(
    body: SupportChatRequest,
    session=None,
) -> SupportChatResponse:
    from app.tickets import infer_category, should_suggest_ticket
    from ckac_common.platform_config import get_platform_secret, third_party_integrations_enabled

    if not (body.message or "").strip() and not body.selected_option_id:
        # Opening turn — main menu
        pack = _pack()
        reply, opts = pack.format_main_menu(body.audience)
        greeting = OWNER_GREETING if body.audience == "owner" else CUSTOMER_GREETING
        return SupportChatResponse(
            audience=body.audience,
            reply=f"{greeting}\n\n{reply}",
            source="knowledge",
            answer_id="support.main_menu",
            options=[SupportOption(id=o["id"], label=o["label"]) for o in opts],
        )

    pack = _pack()
    prior = [{"id": o.id, "label": o.label} for o in body.prior_options]
    turn = pack.resolve_support_turn(
        body.audience,
        body.message or "",
        selected_option_id=body.selected_option_id,
        prior_options=prior or None,
    )

    suggest = turn.suggest_ticket or should_suggest_ticket(
        body.message or "", turn.used_fallback
    )
    category = turn.suggested_category
    if suggest and not category:
        category = infer_category(body.message or "", body.audience)

    options = [SupportOption(id=o["id"], label=o["label"]) for o in (turn.options or [])]
    reply = turn.reply
    source: Literal["knowledge", "ai"] = "knowledge"

    api_key = (
        await get_platform_secret(session, "support_ai_api_key") if session is not None else None
    ) or ""
    if not api_key:
        api_key = os.environ.get("SUPPORT_AI_API_KEY", "").strip()
    tp_on = await third_party_integrations_enabled(session, default=False)

    # Only polish with LLM when we have a solid FAQ hit (not pure fallback menus)
    if api_key and tp_on and turn.answer_id and not turn.used_fallback:
        grounding = pack.faq_grounding_blob(body.audience)
        ai = await _ai_reply(
            body.audience,
            body.message,
            body.history,
            api_key,
            grounding=grounding,
            pack_reply=turn.reply,
        )
        if ai:
            reply = ai
            source = "ai"

    if suggest:
        reply += (
            "\n\nI can log this for our support team — tap **Raise ticket** below "
            "(include order/kitchen code). We follow up within 24 hours on weekdays."
        )

    return SupportChatResponse(
        audience=body.audience,
        reply=reply,
        source=source,
        answer_id=turn.answer_id,
        options=options,
        suggest_ticket=suggest,
        suggested_category=category,
    )
