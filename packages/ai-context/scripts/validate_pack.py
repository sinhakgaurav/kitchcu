#!/usr/bin/env python3
"""Validate kitchCU AI context pack structure and option trees."""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore

ROOT = Path(__file__).resolve().parents[1]
ERRORS: list[str] = []


def err(msg: str) -> None:
    ERRORS.append(msg)


def load_yaml(path: Path):
    if yaml is None:
        err("PyYAML not installed — skip YAML deep checks (pip install pyyaml)")
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def check_menus() -> None:
    menu_dir = ROOT / "menus"
    answer_ids: set[str] = set()
    for faq in (ROOT / "knowledge" / "faq").glob("*.yaml"):
        data = load_yaml(faq)
        if not data:
            continue
        for e in data.get("entries") or []:
            answer_ids.add(e["answer_id"])

    for path in sorted(menu_dir.glob("*.json")):
        menu = json.loads(path.read_text(encoding="utf-8"))
        opts = menu.get("options") or []
        if not 3 <= len(opts) <= 6:
            err(f"{path.name}: expected 3-6 options, got {len(opts)}")
        ids = [o.get("id") for o in opts]
        if len(ids) != len(set(ids)):
            err(f"{path.name}: duplicate option ids")
        for o in opts:
            if not o.get("title"):
                err(f"{path.name}: option missing title")
            aid = o.get("answer_id")
            if aid and answer_ids and aid not in answer_ids:
                err(f"{path.name}: unknown answer_id {aid}")


def check_faq_unique() -> None:
    for faq in (ROOT / "knowledge" / "faq").glob("*.yaml"):
        data = load_yaml(faq)
        if not data:
            continue
        ids = [e["answer_id"] for e in data.get("entries") or []]
        if len(ids) != len(set(ids)):
            err(f"{faq.name}: duplicate answer_id")
        for e in data.get("entries") or []:
            if not e.get("canonical_answer"):
                err(f"{faq.name}: {e.get('answer_id')} missing canonical_answer")
            if not e.get("paraphrases"):
                err(f"{faq.name}: {e.get('answer_id')} missing paraphrases")


def check_fewshots() -> None:
    for name in (
        "order_parse_examples.jsonl",
        "menu_ingest_examples.jsonl",
        "support_dialogues.jsonl",
    ):
        path = ROOT / "fewshot" / name
        if not path.is_file():
            err(f"missing {path}")
            continue
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                json.loads(line)
            except json.JSONDecodeError as exc:
                err(f"{name}:{i}: {exc}")


def check_required_files() -> None:
    required = [
        "README.md",
        "design/WHATSAPP-AI-ASSISTANT-DESIGN.md",
        "prompts/system/core_guardrails.md",
        "prompts/thinking/reason_then_options.md",
        "knowledge/product_facts.yaml",
        "intents/registry.yaml",
    ]
    for rel in required:
        if not (ROOT / rel).is_file():
            err(f"missing {rel}")


def main() -> int:
    check_required_files()
    check_faq_unique()
    check_menus()
    check_fewshots()
    if ERRORS:
        print("AI context pack INVALID:")
        for e in ERRORS:
            print(f"  - {e}")
        return 1
    print(f"AI context pack OK ({ROOT})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
