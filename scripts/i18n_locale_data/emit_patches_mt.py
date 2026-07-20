# -*- coding: utf-8 -*-
"""Generate new-key locale patches via Google Translate (deep-translator).

Preserves {{placeholders}}. Writes scripts/i18n_locale_data/<locale>.json
for MT locales. Keeps curated hi.json / mr.json untouched.

Also builds full bho/mai catalogs into locales/ later via rebuild script;
this emitter writes new-key patches for bho/mai and full-base overlays
for the original 184 keys (from English → bho/mai).
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

from deep_translator import GoogleTranslator

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LOCALES = ROOT / "apps" / "website" / "src" / "i18n" / "locales"
ADDITIONS = HERE.parent / "_i18n_en_additions.json"

# Curated locales — do not overwrite
CURATED = {"hi", "mr"}

# Locales to MT for new keys
MT_NEW = ("te", "pa", "bn", "kn", "ml", "ta", "gu", "bho", "mai")

# Full catalog MT for brand-new locales (base keys not in existing files)
FULL_MT = ("bho", "mai")

PH_RE = re.compile(r"\{\{[^}]+\}\}")


def flatten(node: object, prefix: str = "") -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in node.items():  # type: ignore[union-attr]
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            out.update(flatten(value, path))
        else:
            out[path] = str(value)
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


def protect(text: str) -> tuple[str, dict[str, str]]:
    ph: dict[str, str] = {}

    def repl(m: re.Match[str]) -> str:
        token = f"XPH{len(ph)}X"
        ph[token] = m.group(0)
        return token

    return PH_RE.sub(repl, text), ph


def restore(text: str, ph: dict[str, str]) -> str:
    for token, original in ph.items():
        # translators sometimes alter token casing/spacing
        text = text.replace(token, original)
        text = text.replace(token.lower(), original)
        text = text.replace(token.upper(), original)
    # Ensure originals present
    for original in ph.values():
        if original not in text:
            # append missing placeholder rather than drop
            text = f"{text} {original}".strip()
    return text


def translate_map(en_flat: dict[str, str], target: str) -> dict[str, str]:
    translator = GoogleTranslator(source="en", target=target)
    out: dict[str, str] = {}
    items = list(en_flat.items())
    batch_size = 20
    for i in range(0, len(items), batch_size):
        chunk = items[i : i + batch_size]
        protected: list[str] = []
        ph_list: list[dict[str, str]] = []
        for _, val in chunk:
            p, ph = protect(val)
            protected.append(p)
            ph_list.append(ph)
        try:
            translated = translator.translate_batch(protected)
        except Exception:
            # fallback one-by-one
            translated = []
            for p in protected:
                try:
                    translated.append(translator.translate(p))
                    time.sleep(0.05)
                except Exception as exc:
                    print(f"  WARN translate fail ({target}): {exc}")
                    translated.append(p)
        if not isinstance(translated, list) or len(translated) != len(chunk):
            # deep-translator sometimes returns fewer; redo singly
            translated = []
            for p in protected:
                translated.append(translator.translate(p))
                time.sleep(0.05)
        for (key, _), tr, ph in zip(chunk, translated, ph_list):
            out[key] = restore(tr if isinstance(tr, str) else str(tr), ph)
        print(f"  {target}: {min(i + batch_size, len(items))}/{len(items)}", flush=True)
        time.sleep(0.1)
    return out


def main() -> int:
    additions = json.loads(ADDITIONS.read_text(encoding="utf-8"))
    new_flat = flatten(additions)
    print(f"new keys: {len(new_flat)}")

    en_full = flatten(json.loads((LOCALES / "en.json").read_text(encoding="utf-8")))
    # If en not yet expanded, merge additions for base keys of new locales
    for k, v in new_flat.items():
        en_full.setdefault(k, v)

    # Existing locale base keys (for FULL_MT difference)
    hi_existing = flatten(json.loads((LOCALES / "hi.json").read_text(encoding="utf-8")))
    base_keys = {k: en_full[k] for k in hi_existing if k in en_full and k not in new_flat}
    print(f"base keys for full MT: {len(base_keys)}")

    for code in MT_NEW:
        if code in CURATED:
            continue
        out_path = HERE / f"{code}.json"
        if out_path.is_file() and flatten(json.loads(out_path.read_text(encoding="utf-8"))) == {}:
            pass
        if out_path.is_file():
            existing = flatten(json.loads(out_path.read_text(encoding="utf-8")))
            if set(existing) >= set(new_flat):
                print(f"skip {code}.json (already complete, {len(existing)} keys)", flush=True)
                continue
        print(f"Translating new keys → {code}", flush=True)
        mapped = translate_map(new_flat, code)
        nested = unflatten(mapped)
        out_path.write_text(
            json.dumps(nested, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"wrote {code}.json ({len(mapped)} keys)", flush=True)

    for code in FULL_MT:
        out_path = HERE / f"{code}_base_overlay.json"
        if out_path.is_file():
            existing = flatten(json.loads(out_path.read_text(encoding="utf-8")))
            if set(existing) >= set(base_keys):
                print(f"skip {out_path.name} (already complete, {len(existing)} keys)", flush=True)
                continue
        print(f"Translating base keys → {code}_base_overlay", flush=True)
        mapped = translate_map(base_keys, code)
        nested = unflatten(mapped)
        out_path.write_text(
            json.dumps(nested, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"wrote {code}_base_overlay.json ({len(mapped)} keys)", flush=True)

    print("EMIT OK", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
