#!/usr/bin/env python3
"""Rebuild website i18n locale catalogs with full key parity.

- Merges new English keys into en.json (preserving existing values)
- Reuses existing translated leaves for hi/mr/ta/te/kn/ml/bn/gu/pa
- Applies new-key translations from scripts/i18n_locale_data/<locale>.json
- Builds bho.json / mai.json (full catalogs) from Hindi base + overlays
- Pretty-prints UTF-8 JSON for all locales

Run: python scripts/rebuild-i18n-catalogs.py
"""
from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCALES_DIR = ROOT / "apps" / "website" / "src" / "i18n" / "locales"
DATA_DIR = Path(__file__).resolve().parent / "i18n_locale_data"
ADDITIONS_PATH = Path(__file__).resolve().parent / "_i18n_en_additions.json"

EXISTING_LOCALES = ("hi", "mr", "ta", "te", "kn", "ml", "bn", "gu", "pa")
ALL_LOCALES = EXISTING_LOCALES + ("bho", "mai")


def flatten(node: object, prefix: str = "") -> dict[str, str]:
    if not isinstance(node, dict):
        raise ValueError(f"expected object at {prefix or '<root>'}")
    out: dict[str, str] = {}
    for key, value in node.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            out.update(flatten(value, path))
        elif isinstance(value, str):
            out[path] = value
        else:
            raise ValueError(f"leaf must be string at {path}")
    return out


def unflatten(flat: dict[str, str]) -> dict:
    root: dict = {}
    for path, value in flat.items():
        parts = path.split(".")
        cur = root
        for part in parts[:-1]:
            cur = cur.setdefault(part, {})
        cur[parts[-1]] = value
    return root


def deep_merge(base: dict, overlay: dict) -> dict:
    out = deepcopy(base)
    for key, value in overlay.items():
        if key in out and isinstance(out[key], dict) and isinstance(value, dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = deepcopy(value)
    return out


def write_json(path: Path, data: dict) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_placeholders(en_flat: dict[str, str], loc_flat: dict[str, str], locale: str) -> None:
    import re

    pat = re.compile(r"\{\{[^}]+\}\}")
    for key, en_val in en_flat.items():
        loc_val = loc_flat[key]
        en_ph = sorted(pat.findall(en_val))
        loc_ph = sorted(pat.findall(loc_val))
        if en_ph != loc_ph:
            raise SystemExit(
                f"FAIL {locale}: placeholder mismatch at {key}: en={en_ph} loc={loc_ph}"
            )


def hindi_to_bhojpuri(text: str) -> str:
    """Light spoken-form adaptation from Hindi UI → Bhojpuri (Devanagari)."""
    reps = [
        ("आपकी", "रउरा"),
        ("आपका", "रउरा"),
        ("आपको", "रउरा के"),
        ("आप ", "रउआ "),
        ("हैं।", "बानी।"),
        ("हैं?", "बानी?"),
        ("हैं", "बानी"),
        (" है।", " बा।"),
        (" है?", " बा?"),
        (" है,", " बा,"),
        (" है ", " बा "),
        ("रहा है", "रहल बा"),
        ("रही है", "रहल बा"),
        ("चुनें", "चुनीं"),
        ("करें", "करीं"),
        ("जारी रखें", "जारी राखीं"),
        ("सहेजें", "सेव करीं"),
        ("खोजें", "खोजीं"),
        ("देखें", "देखीं"),
        ("कृपया", "मेहरबानी करके"),
        ("धन्यवाद", "धन्यवाद"),
        ("लोड हो रहा है", "लोड हो रहल बा"),
    ]
    out = text
    for a, b in reps:
        out = out.replace(a, b)
    return out


def hindi_to_maithili(text: str) -> str:
    """Light spoken-form adaptation from Hindi UI → Maithili (Devanagari)."""
    reps = [
        ("आपकी", "अहाँक"),
        ("आपका", "अहाँक"),
        ("आपको", "अहाँकेँ"),
        ("आप ", "अहाँ "),
        ("हैं।", "अछि।"),
        ("हैं?", "अछि?"),
        ("हैं", "अछि"),
        (" है।", " अछि।"),
        (" है?", " अछि?"),
        (" है,", " अछि,"),
        (" है ", " अछि "),
        ("रहा है", "छल अछि"),
        ("रही है", "छल अछि"),
        ("चुनें", "चुनू"),
        ("करें", "करू"),
        ("जारी रखें", "जारी राखू"),
        ("सहेजें", "सहेजू"),
        ("खोजें", "खोजू"),
        ("देखें", "देखू"),
        ("कृपया", "कृपा कऽ"),
        ("लोड हो रहा है", "लोड भऽ रहल अछि"),
    ]
    out = text
    for a, b in reps:
        out = out.replace(a, b)
    return out


def build_adapted_catalog(hi: dict, adapter) -> dict:
    flat = flatten(hi)
    adapted = {k: adapter(v) for k, v in flat.items()}
    return unflatten(adapted)


def main() -> int:
    additions = load_json(ADDITIONS_PATH)
    en_path = LOCALES_DIR / "en.json"
    en_base = load_json(en_path)
    en = deep_merge(en_base, additions)
    write_json(en_path, en)
    en_flat = flatten(en)
    print(f"en.json: {len(en_flat)} keys")

    # Existing locales: reuse prior translations, merge new-key patches
    for code in EXISTING_LOCALES:
        path = LOCALES_DIR / f"{code}.json"
        existing = load_json(path)
        patch_path = DATA_DIR / f"{code}.json"
        if not patch_path.is_file():
            print(f"FAIL: missing patch {patch_path}")
            return 1
        patch = load_json(patch_path)
        merged = deep_merge(existing, patch)
        # Ensure every en key present; fill gaps from patch only (should be complete)
        flat = flatten(merged)
        missing = sorted(set(en_flat) - set(flat))
        if missing:
            print(f"FAIL {code}: missing after merge ({len(missing)}): {missing[:8]}")
            return 1
        # Drop extras not in en
        flat = {k: flat[k] for k in en_flat}
        assert_placeholders(en_flat, flat, code)
        write_json(path, unflatten(flat))
        print(f"{code}.json: {len(flat)} keys")

    # bho / mai: Hindi spoken adaptation as fallback, then MT overlays + new-key patches
    hi = load_json(LOCALES_DIR / "hi.json")
    adapters = {"bho": hindi_to_bhojpuri, "mai": hindi_to_maithili}
    for code, adapter in adapters.items():
        base = build_adapted_catalog(hi, adapter)
        overlay_path = DATA_DIR / f"{code}_base_overlay.json"
        if overlay_path.is_file():
            base = deep_merge(base, load_json(overlay_path))
        patch_path = DATA_DIR / f"{code}.json"
        if not patch_path.is_file():
            print(f"FAIL: missing patch {patch_path}")
            return 1
        patch = load_json(patch_path)
        merged = deep_merge(base, patch)
        flat = flatten(merged)
        missing = sorted(set(en_flat) - set(flat))
        if missing:
            print(f"FAIL {code}: missing ({len(missing)}): {missing[:8]}")
            return 1
        flat = {k: flat[k] for k in en_flat}
        assert_placeholders(en_flat, flat, code)
        # New locales start from adapted hi which already includes new hi keys
        write_json(LOCALES_DIR / f"{code}.json", unflatten(flat))
        print(f"{code}.json: {len(flat)} keys")

    print("REBUILD OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
