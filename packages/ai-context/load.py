"""Helpers to load AI context pack files from disk."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent


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
    # Expand simple includes relative to prompts/
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
    """Naive paraphrase contains-match → answer_id (for KB bootstrapping)."""
    data = faq(audience)
    m = message.lower()
    best: str | None = None
    best_hits = 0
    for entry in data.get("entries") or []:
        hits = 0
        for p in entry.get("paraphrases") or []:
            token = p.lower()
            if len(token) >= 4 and token in m:
                hits += 2
            else:
                for word in token.split():
                    if len(word) > 3 and word in m:
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
