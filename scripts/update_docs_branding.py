#!/usr/bin/env python3
"""Update docs and PDF generator sources: CKAC product branding -> Kitchcu."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SCRIPTS = ROOT / "scripts"

# Protect internal identifiers and file names from product rename
PROTECT_PATTERNS = [
    r"CKAC-[A-Z0-9\-]+\.(?:md|pdf)",
    r"`ckac_[a-z0-9_]+`",
    r"ckac_[a-z][a-z0-9_]*",
    r"CKAC/",
    r"ckac-common",
    r"CKAC_[A-Z0-9_]+",
    r"packages/ckac-common",
    r"ckac:<[a-z:]+>",
    r"ckac\.<domain>",
]


def protect(text: str) -> tuple[str, list[str]]:
    tokens: list[str] = []

    def _sub(m: re.Match[str]) -> str:
        tokens.append(m.group(0))
        return f"__PROT{len(tokens) - 1}__"

    for pat in PROTECT_PATTERNS:
        text = re.sub(pat, _sub, text)
    return text, tokens


def restore(text: str, tokens: list[str]) -> str:
    for i, tok in enumerate(tokens):
        text = text.replace(f"__PROT{i}__", tok)
    return text


def rebrand_text(text: str) -> str:
    text, tokens = protect(text)
    subs = [
        (r"\bCKAC\b", "kitchCU"),
        (r"customer\.ckac\b", "customer.kitchcu.in"),
        (r"kitchen\.ckac\b", "kitchen.kitchcu.in"),
        (r"admin\.ckac\b", "admin.kitchcu.in"),
        (r"customer\.kitchcu(?!\.in)\b", "customer.kitchcu.in"),
        (r"kitchen\.kitchcu(?!\.in)\b", "kitchen.kitchcu.in"),
        (r"admin\.kitchcu(?!\.in)\b", "admin.kitchcu.in"),
        (r"admin@ckac\.dev", "admin@kitchcu.dev"),
        (r"hello@ckac\.in", "hello@kitchcu.in"),
        (r"demo@ckac\.dev", "demo@kitchcu.dev"),
        (r"Cloud Kitchen Analytics, Order & Management Platform with Marketing", "kitchCU cloud kitchen platform"),
        (r"Cloud Kitchen Analytics & Control", "kitchCU Cloud Kitchen Platform"),
    ]
    for pat, repl in subs:
        text = re.sub(pat, repl, text)
    return restore(text, tokens)


def update_file(path: Path) -> bool:
    original = path.read_text(encoding="utf-8")
    updated = rebrand_text(original)
    if updated != original:
        path.write_text(updated, encoding="utf-8")
        return True
    return False


def main() -> None:
    changed: list[str] = []
    for path in sorted(DOCS.glob("*.md")):
        if update_file(path):
            changed.append(str(path.relative_to(ROOT)))
    for name in (
        "generate_complete_guide_pdf.py",
        "generate_product_depth_pdf.py",
        "generate_pitch_pdf.py",
        "pdf_guide.py",
        "pdf_common.py",
    ):
        path = SCRIPTS / name
        if path.is_file() and update_file(path):
            changed.append(str(path.relative_to(ROOT)))
    print(f"Updated {len(changed)} files:")
    for c in changed:
        print(f"  - {c}")


if __name__ == "__main__":
    main()
