"""Helpers to load AI context pack files from disk."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent

_TICKET_LABEL = re.compile(r"\b(ticket|human|agent|complaint|refund dispute)\b", re.I)
_GREETING = re.compile(
    r"^(hi|hello|hey|hii|help|menu|start|options|main menu|back|back to main|"
    r"back to main menu)\b",
    re.I,
)


@lru_cache(maxsize=1)
def product_facts() -> dict[str, Any]:
    import yaml

    return yaml.safe_load((ROOT / "knowledge" / "product_facts.yaml").read_text(encoding="utf-8"))


@lru_cache(maxsize=4)
def faq(audience: str) -> dict[str, Any]:
    import yaml

    path = ROOT / "knowledge" / "faq" / f"{audience}.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def menu(menu_id: str) -> dict[str, Any]:
    path = ROOT / "menus" / f"{menu_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def system_prompt(name: str) -> str:
    """Load a system prompt markdown file (does not expand {{include}})."""
    path = ROOT / "prompts" / "system" / name
    if not path.suffix:
        path = path.with_suffix(".md")
    text = path.read_text(encoding="utf-8")
    out_lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("{{include:") and line.endswith("}}"):
            rel = line[len("{{include:") : -2].strip()
            inc = (path.parent / rel).resolve()
            if inc.is_file():
                out_lines.append(inc.read_text(encoding="utf-8"))
                out_lines.append("")
            else:
                out_lines.append(f"<!-- missing include {rel} -->")
        else:
            out_lines.append(line)
    return "\n".join(out_lines)


def match_answer_id(audience: str, message: str) -> str | None:
    """Paraphrase / keyword score → best answer_id."""
    data = faq(audience)
    m = message.lower().strip()
    best: str | None = None
    best_hits = 0
    for entry in data.get("entries") or []:
        hits = 0
        for p in entry.get("paraphrases") or []:
            token = (p or "").lower().strip()
            if not token:
                continue
            if len(token) >= 4 and token in m:
                hits += 3
            else:
                words = [w for w in re.split(r"\W+", token) if len(w) > 3]
                matched = sum(1 for w in words if w in m)
                if words and matched >= max(1, len(words) // 2):
                    hits += matched
        # answer_id topic tokens as soft boost
        for part in str(entry.get("answer_id") or "").split("."):
            if len(part) > 3 and part in m:
                hits += 1
        if hits > best_hits:
            best_hits = hits
            best = entry.get("answer_id")
    return best if best_hits >= 2 else None


def canonical_answer(audience: str, answer_id: str) -> str | None:
    data = faq(audience)
    for entry in data.get("entries") or []:
        if entry.get("answer_id") == answer_id:
            return (entry.get("canonical_answer") or "").strip()
    return None


def option_set(audience: str, option_set_id: str | None) -> list[dict[str, str]]:
    if not option_set_id:
        return []
    data = faq(audience)
    raw = (data.get("option_sets") or {}).get(option_set_id) or []
    return [{"id": str(o.get("id")), "label": str(o.get("label"))} for o in raw]


def entry_option_set_id(audience: str, answer_id: str) -> str | None:
    data = faq(audience)
    for entry in data.get("entries") or []:
        if entry.get("answer_id") == answer_id:
            return entry.get("option_set_id")
    return None


def main_menu_id(audience: str) -> str:
    return "kitchen_main" if audience == "owner" else "customer_main"


def main_menu_options(audience: str) -> list[dict[str, str]]:
    m = menu(main_menu_id(audience))
    return [{"id": str(o["id"]), "title": str(o["title"]), **o} for o in m.get("options") or []]


def format_main_menu(audience: str) -> tuple[str, list[dict[str, str]]]:
    m = menu(main_menu_id(audience))
    header = m.get("header") or "kitchCU help"
    body = m.get("body") or "Choose an option:"
    opts = [
        {"id": str(o["id"]), "label": str(o.get("title") or o.get("label") or o["id"])}
        for o in m.get("options") or []
    ]
    lines = [f"**{header}**", "", body, ""]
    for o in opts:
        lines.append(f"{o['id']}) {o['label']}")
    lines.append("")
    lines.append("Or type your question in plain language.")
    return "\n".join(lines), opts


@dataclass
class SupportTurn:
    reply: str
    answer_id: str | None = None
    options: list[dict[str, str]] = field(default_factory=list)
    suggest_ticket: bool = False
    suggested_category: str | None = None
    used_fallback: bool = False
    source: str = "knowledge"


_OPTION_TO_ANSWER: dict[str, dict[str, str]] = {
    # Follow-up labels that map across option sets → FAQ
    "owner": {
        "pricing plans": "owner.pricing.plans",
        "pricing": "owner.pricing.plans",
        "subscription plans": "owner.pricing.plans",
        "why owners pay (cost breakdown)": "owner.pricing.why_charge",
        "compare starter vs growth": "owner.pricing.plans",
        "whatsapp orders": "owner.whatsapp.orders",
        "whatsapp draft help": "owner.whatsapp.orders",
        "whatsapp setup": "owner.whatsapp.orders",
        "menu setup": "owner.menu.live_capture",
        "live-capture rules": "owner.menu.live_capture",
        "create first dish": "owner.menu.live_capture",
        "add dish walkthrough": "owner.menu.live_capture",
        "import catalog from whatsapp": "owner.menu.from_whatsapp",
        "how live photos work": "owner.menu.live_capture",
        "growth reports": "owner.reports.growth",
        "order lifecycle": "owner.orders.lifecycle",
        "manual new order": "owner.orders.lifecycle",
        "how refunds work": "owner.billing.refunds",
        "coupons & crm": "owner.marketing.crm",
        "crm & coupons": "owner.marketing.crm",
        "referrals": "owner.referrals.program",
        "dashboard sections": "owner.reports.growth",
        "back to dashboard sections": "owner.reports.growth",
        "open orders section help": "owner.orders.lifecycle",
        "show parse example": "owner.whatsapp.orders",
        "paste catalog text now": "owner.menu.from_whatsapp",
    },
    "customer": {
        "find a kitchen": "customer.find.kitchen",
        "enter kitchen code help": "customer.find.kitchen",
        "how ordering works": "customer.order.checkout",
        "order online": "customer.order.checkout",
        "track my order": "customer.order.track",
        "payment options": "customer.payment.options",
        "live-capture photos": "customer.trust.live_capture",
        "why customers are charged": "customer.pricing.why_charge",
        "pricing for kitchens": "owner.pricing.plans",
        "find kitchen contact": "customer.support.contact",
        "order issue ticket": "customer.support.contact",
    },
}


def _ticket_category_hint(message: str, audience: str) -> str:
    m = message.lower()
    if any(w in m for w in ("refund", "invoice", "subscription", "gst", "payment failed", "billing")):
        return "billing"
    if any(w in m for w in ("deliver", "tracking", "rider", "late")):
        return "delivery"
    if any(w in m for w in ("taste", "quality", "spoiled", "cold", "hygiene")):
        return "quality"
    if any(w in m for w in ("order", "cancel", "missing item", "wrong item")):
        return "order_issue"
    if any(w in m for w in ("login", "otp", "bug", "error", "crash", "technical")):
        return "technical"
    if "complaint" in m or "fraud" in m:
        return "complaint"
    return "general"


def _resolve_menu_option(audience: str, option_id: str) -> SupportTurn | None:
    for o in menu(main_menu_id(audience)).get("options") or []:
        if str(o.get("id")) != str(option_id):
            continue
        intent = o.get("intent")
        if intent == "support.ticket.start":
            return SupportTurn(
                reply=(
                    "I can open a support ticket for our human team.\n\n"
                    "Click **Raise ticket** below — include kitchen code / order code if you have one. "
                    "We reply within 24 hours on weekdays (hello@kitchcu.in)."
                ),
                answer_id=None,
                options=[
                    {"id": "1", "label": "Back to main menu"},
                    {"id": "2", "label": "Pricing plans" if audience == "owner" else "Find a kitchen"},
                ],
                suggest_ticket=True,
                suggested_category="general",
            )
        answer_id = o.get("answer_id")
        if answer_id:
            return _turn_from_answer(audience, answer_id)
    return None


def _turn_from_answer(audience: str, answer_id: str) -> SupportTurn:
    text = canonical_answer(audience, answer_id) or ""
    opts = option_set(audience, entry_option_set_id(audience, answer_id))
    suggest = "ticket" in answer_id or "support.contact" in answer_id
    return SupportTurn(
        reply=text,
        answer_id=answer_id,
        options=opts
        or [
            {"id": "1", "label": "Back to main menu"},
            {"id": "2", "label": "Raise a ticket"},
        ],
        suggest_ticket=suggest,
        suggested_category=_ticket_category_hint(answer_id, audience) if suggest else None,
        used_fallback=not bool(text),
    )


def _match_option_label(audience: str, message: str, prior_options: list[dict[str, str]] | None) -> SupportTurn | None:
    m = message.lower().strip()
    # Numbered reply
    if re.fullmatch(r"\d{1,2}", m):
        if prior_options:
            for o in prior_options:
                if str(o.get("id")) == m:
                    return _resolve_label_or_menu(audience, o.get("label") or "", m)
        return _resolve_menu_option(audience, m)

    # Exact / contains label from prior chips
    if prior_options:
        for o in prior_options:
            label = (o.get("label") or "").lower()
            if label and (m == label or label in m or m in label):
                return _resolve_label_or_menu(audience, o.get("label") or "", str(o.get("id")))

    # Global label map
    mapped = _OPTION_TO_ANSWER.get(audience, {}).get(m)
    if mapped:
        # Cross-audience leak: customer asking owner pricing — keep on customer about
        if audience == "customer" and mapped.startswith("owner."):
            return _turn_from_answer("customer", "customer.about.platform")
        return _turn_from_answer(audience, mapped)
    return None


def _resolve_label_or_menu(audience: str, label: str, option_id: str) -> SupportTurn:
    low = label.lower().strip()
    if "main menu" in low or low in ("back", "back to main"):
        reply, opts = format_main_menu(audience)
        return SupportTurn(reply=reply, options=opts, answer_id="support.main_menu")
    if "ticket" in low or "talk to support" in low:
        return SupportTurn(
            reply=(
                "I'll help you reach a human.\n\n"
                "Click **Raise ticket** below and share kitchen/order details. "
                "Email: **hello@kitchcu.in**."
            ),
            options=[{"id": "1", "label": "Back to main menu"}],
            suggest_ticket=True,
            suggested_category=_ticket_category_hint(label, audience),
        )
    mapped = _OPTION_TO_ANSWER.get(audience, {}).get(low)
    if mapped:
        return _turn_from_answer(audience, mapped)
    # Try main menu id
    menu_hit = _resolve_menu_option(audience, option_id)
    if menu_hit:
        return menu_hit
    # Fallback: treat label as free text FAQ
    aid = match_answer_id(audience, label)
    if aid:
        return _turn_from_answer(audience, aid)
    reply, opts = format_main_menu(audience)
    return SupportTurn(reply=reply, options=opts, answer_id="support.main_menu", used_fallback=True)


def resolve_support_turn(
    audience: str,
    message: str,
    *,
    selected_option_id: str | None = None,
    prior_options: list[dict[str, str]] | None = None,
) -> SupportTurn:
    """Options-first support resolver used by the notification service."""
    audience = "owner" if audience == "owner" else "customer"
    text = (message or "").strip()

    if selected_option_id:
        hit = _resolve_menu_option(audience, selected_option_id)
        if hit:
            return hit
        if prior_options:
            for o in prior_options:
                if str(o.get("id")) == str(selected_option_id):
                    return _resolve_label_or_menu(audience, o.get("label") or "", str(selected_option_id))

    if not text or _GREETING.match(text):
        reply, opts = format_main_menu(audience)
        return SupportTurn(reply=reply, options=opts, answer_id="support.main_menu")

    opt_hit = _match_option_label(audience, text, prior_options)
    if opt_hit:
        return opt_hit

    if _TICKET_LABEL.search(text) and match_answer_id(audience, text) is None:
        cat = _ticket_category_hint(text, audience)
        return SupportTurn(
            reply=(
                "Sounds like you may need a human follow-up.\n\n"
                "I can still answer product questions — or click **Raise ticket** and we'll "
                f"route this as **{cat.replace('_', ' ')}**."
            ),
            options=[
                {"id": "1", "label": "Back to main menu"},
                {"id": "2", "label": "Pricing plans" if audience == "owner" else "Track my order"},
            ],
            suggest_ticket=True,
            suggested_category=cat,
        )

    aid = match_answer_id(audience, text)
    if aid:
        return _turn_from_answer(audience, aid)

    # Soft fallback with main menu (never invent features)
    reply, opts = format_main_menu(audience)
    soft = (
        "I'm not sure I caught that — here's what I can help with.\n\n" + reply
        if audience == "owner"
        else "Let me show the best ways I can help.\n\n" + reply
    )
    return SupportTurn(
        reply=soft,
        options=opts,
        answer_id=None,
        used_fallback=True,
        suggest_ticket=False,
    )


def faq_grounding_blob(audience: str, limit: int = 8) -> str:
    """Compact FAQ text for LLM grounding."""
    data = faq(audience)
    chunks: list[str] = []
    for entry in (data.get("entries") or [])[:limit]:
        aid = entry.get("answer_id")
        ans = (entry.get("canonical_answer") or "").strip().replace("\n", " ")
        chunks.append(f"[{aid}] {ans[:280]}")
    return "\n".join(chunks)
