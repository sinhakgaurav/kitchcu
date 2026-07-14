"""kitchCU support assistant — owner & customer help on the marketing site.

Uses a curated knowledge base with keyword routing. When SUPPORT_AI_API_KEY is
set, augments replies via OpenAI-compatible chat API; otherwise returns
deterministic, accurate answers (no hallucinated pricing or features).
"""

from __future__ import annotations

import os
import re
from typing import Literal

import httpx
from pydantic import BaseModel, Field

Audience = Literal["owner", "customer"]

OWNER_GREETING = (
    "Hi! I'm the kitchCU owner assistant. I can help with pricing, WhatsApp orders, "
    "menus, analytics, onboarding, and kitchen setup. What would you like to know?"
)

CUSTOMER_GREETING = (
    "Hello! I'm here to help customers browse kitchens, find menus, understand "
    "live-capture photos, and order from home food businesses. How can I help?"
)

FALLBACK_OWNER = (
    "I'm not sure about that yet. For owner help, email hello@kitchCU.in or use the "
    "contact form. Common topics: pricing (from ₹499/mo), WhatsApp orders, menu setup, "
    "growth reports, and OTP login on kitchen.kitchCU.in."
)

FALLBACK_CUSTOMER = (
    "I can help you find kitchens, browse menus, and understand how kitchCU works. "
    "Try asking about kitchen codes, nearby kitchens, live photos, or delivery. "
    "For urgent issues, email hello@kitchCU.in."
)


class ChatMessage(BaseModel):
    """One turn in a support chat history."""

    role: Literal["user", "assistant"] = Field(..., description="Who sent this turn.")
    content: str = Field(..., min_length=1, max_length=2000, description="Message text.")


class SupportChatRequest(BaseModel):
    """Marketing-site AI support chat request."""

    audience: Audience = Field(..., description="'owner' or 'customer' — selects the knowledge base and system prompt tone.")
    message: str = Field(..., min_length=1, max_length=2000, description="The user's latest message.")
    history: list[ChatMessage] = Field(default_factory=list, max_length=20, description="Prior turns in this conversation, oldest first (used for LLM context, last 8 kept).")


class SupportChatResponse(BaseModel):
    """AI/knowledge-base support reply, with an optional ticket-raising prompt."""

    audience: Audience = Field(..., description="Echoes the request audience.")
    reply: str = Field(..., description="Assistant's reply text (markdown-formatted).")
    source: Literal["knowledge", "ai"] = Field(..., description="'knowledge' — deterministic curated answer (no LLM configured/available). 'ai' — LLM-augmented reply.")
    suggest_ticket: bool = Field(default=False, description="True when the message pattern suggests escalation (complaint, refund, explicit request for a human) — the UI should offer 'Raise ticket'.")
    suggested_category: str | None = Field(default=None, description="Pre-filled ticket category inferred from the message, when `suggest_ticket` is true.")


def _match(text: str, *patterns: str) -> bool:
    return any(re.search(p, text) for p in patterns)


def _owner_reply(message: str) -> str | None:
    m = message.lower().strip()

    if _match(m, r"\b(price|pricing|plan|cost|subscription|fee|commission|charge)\b"):
        return (
            "kitchCU is **subscription-only — zero food commission** on orders.\n\n"
            "• **Starter** — ₹499/mo: 1 kitchen, manual + WhatsApp orders, live-capture menu\n"
            "• **Growth** — ₹999/mo: growth reports, customer CRM, marketing tools\n"
            "• **Scale** — ₹1,999/mo: multi-kitchen, priority support, advanced analytics\n\n"
            "All plans include order lifecycle and customer menu links. "
            "Request pilot access on the contact form or email hello@kitchCU.in."
        )

    if _match(m, r"\b(whatsapp|wa\b|chat order|parse message)\b"):
        return (
            "WhatsApp orders: customers message your kitchen → kitchCU parses items into a "
            "**draft order** → you review and confirm in one tap on kitchen.kitchCU.in.\n\n"
            "Paste messages in Orders → 'Parse to draft', fix unmatched lines, then confirm. "
            "No per-order commission — you own the customer relationship."
        )

    if _match(m, r"\b(menu|cuisine|dish|category|veg|non.?veg|photo|live.?capture)\b"):
        return (
            "Menu hierarchy: **cuisine → veg/non-veg → dish**. Hero photos must be "
            "**live-capture** (no stock images) to build customer trust.\n\n"
            "Add dishes in kitchen.kitchCU.in → Menu → Add dish. Share your customer menu link "
            "from the dashboard overview."
        )

    if _match(m, r"\b(analytic|report|revenue|repeat|churn|dashboard|growth)\b"):
        return (
            "Growth Reports (kitchen.kitchCU.in → Reports) show:\n"
            "• Revenue & 30-day trend\n"
            "• Top dishes by sales\n"
            "• Peak hours (IST) for prep planning\n"
            "• Repeat-customer rate & VIP segments\n"
            "• Win-back list for customers who haven't ordered in 3+ weeks"
        )

    if _match(m, r"\b(login|sign.?in|otp|register|onboard|start|setup)\b"):
        return (
            "Owner onboarding:\n"
            "1. Open **kitchen.kitchCU.in** → Owner sign in\n"
            "2. Register phone → OTP verify (dev OTP: 123456)\n"
            "3. Create kitchen → add dishes with live photos\n"
            "4. Share customer menu link — first order in under 5 minutes"
        )

    if _match(m, r"\b(order|lifecycle|status|deliver|cancel|manual)\b"):
        return (
            "Order lifecycle: received → accepted → preparing → ready → "
            "out_for_delivery → delivered (or cancelled).\n\n"
            "Create manual orders from the dashboard or confirm WhatsApp drafts. "
            "Track every order on kitchen.kitchCU.in → Orders."
        )

    if _match(m, r"\b(support|help|contact|email|human|agent)\b"):
        return (
            "Human support: **hello@kitchCU.in** · Pune, India · response within 24h on weekdays.\n"
            "Use the contact form on kitchCU.in for pilot access. "
            "Platform admin issues: admin@kitchCU.dev (internal)."
        )

    if _match(m, r"\b(cloud kitchen|home food|tiffin|delivery only)\b"):
        return (
            "kitchCU is built **only for cloud kitchens & home food businesses** — "
            "not restaurants, POS, or dine-in. Ideal for home chefs, tiffin services, "
            "and delivery-only kitchens who want independence from Swiggy/Zomato."
        )

    return None


def _customer_reply(message: str) -> str | None:
    m = message.lower().strip()

    if _match(m, r"\b(find|nearby|discover|kitchen|code|browse|menu)\b"):
        return (
            "Find kitchens on **customer.kitchCU.in**:\n"
            "• Enter a kitchen code (e.g. CKPNQ001) from your home chef\n"
            "• Or use **Nearby** with location to see cloud kitchens sorted by distance\n\n"
            "Menus are grouped by cuisine and veg/non-veg with live-capture dish photos."
        )

    if _match(m, r"\b(live.?capture|photo|trust|real|stock)\b"):
        return (
            "Every hero dish photo on kitchCU is **live-captured in the kitchen** — "
            "no stock images. What you see is what the home chef actually cooks. "
            "That's core to kitchCU's trust promise for home-made food."
        )

    if _match(m, r"\b(order|checkout|pay|cod|upi|cart|buy)\b"):
        return (
            "Today you can **browse menus and discover kitchens** on customer.kitchCU.in. "
            "Online checkout with UPI/COD is coming in the next release.\n\n"
            "For now, order via the kitchen's WhatsApp link or phone — "
            "the owner confirms on kitchen.kitchCU.in."
        )

    if _match(m, r"\b(delivery|pickup|fee|radius|distance)\b"):
        return (
            "Delivery fees and radius are set by each kitchen owner — "
            "fair, transparent pricing without aggregator markups. "
            "Check the kitchen menu page for prep time and delivery options."
        )

    if _match(m, r"\b(rating|review|taste|quality)\b"):
        return (
            "Home taste & quality ratings from verified orders are on the kitchCU roadmap. "
            "kitchCU focuses on trust through live photos and direct kitchen relationships first."
        )

    if _match(m, r"\b(price|pricing|cost|cheap|expensive|commission)\b"):
        return (
            "kitchCU kitchens set their own prices — **no aggregator commission** passed to you. "
            "You pay the kitchen directly (COD/UPI when checkout launches). "
            "Supporting local home food businesses keeps prices fair."
        )

    if _match(m, r"\b(support|help|contact|email|problem|issue)\b"):
        return (
            "Customer support: **hello@kitchCU.in**. For order issues, contact the kitchen "
            "directly first — kitchCU connects you to the home chef, not a call centre."
        )

    if _match(m, r"\b(what is kitchCU|about|platform)\b"):
        return (
            "kitchCU helps you discover and trust **home food businesses & cloud kitchens** "
            "near you. Browse live-capture menus, find kitchens by code or location, "
            "and support local home chefs instead of big aggregators."
        )

    return None


def knowledge_reply(audience: Audience, message: str) -> str:
    if audience == "owner":
        return _owner_reply(message) or FALLBACK_OWNER
    return _customer_reply(message) or FALLBACK_CUSTOMER


async def _ai_reply(
    audience: Audience,
    message: str,
    history: list[ChatMessage],
    api_key: str,
) -> str | None:
    system = (
        "You are kitchCU support assistant for "
        + ("cloud kitchen OWNERS" if audience == "owner" else "CUSTOMERS")
        + ". kitchCU is subscription SaaS for home food & cloud kitchens — NOT restaurants/POS. "
        "Zero food commission. Plans: Starter ₹499, Growth ₹999, Scale ₹1999/month. "
        "Owner app: kitchen.kitchCU.in. Customer app: customer.kitchCU.in. "
        "Be concise, accurate, friendly. Never invent features. "
        "If unsure, direct to hello@kitchCU.in."
    )
    messages = [{"role": "system", "content": system}]
    for h in history[-8:]:
        messages.append({"role": h.role, "content": h.content})
    messages.append({"role": "user", "content": message})

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": os.environ.get("SUPPORT_AI_MODEL", "gpt-4o-mini"),
                    "messages": messages,
                    "max_tokens": 400,
                    "temperature": 0.4,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


async def generate_support_reply(body: SupportChatRequest) -> SupportChatResponse:
    from app.tickets import infer_category, should_suggest_ticket

    api_key = os.environ.get("SUPPORT_AI_API_KEY", "").strip()
    kb = knowledge_reply(body.audience, body.message)
    used_fallback = kb == (FALLBACK_OWNER if body.audience == "owner" else FALLBACK_CUSTOMER)
    suggest = should_suggest_ticket(body.message, used_fallback)
    category = infer_category(body.message, body.audience) if suggest else None

    if api_key:
        ai = await _ai_reply(body.audience, body.message, body.history, api_key)
        if ai:
            ticket_hint = ""
            if suggest:
                ticket_hint = (
                    "\n\nI can log this for our support team — click **Raise ticket** below "
                    "and we'll follow up within 24 hours."
                )
            return SupportChatResponse(
                audience=body.audience,
                reply=ai + ticket_hint,
                source="ai",
                suggest_ticket=suggest,
                suggested_category=category,
            )

    reply = kb
    if suggest:
        reply += (
            "\n\nWould you like me to raise a support ticket? Click **Raise ticket** below — "
            "include your order code if this is order-related. Our team responds within 24 hours."
        )
    return SupportChatResponse(
        audience=body.audience,
        reply=reply,
        source="knowledge",
        suggest_ticket=suggest,
        suggested_category=category,
    )
