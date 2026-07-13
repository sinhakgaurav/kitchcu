"""Rule-based order message parser (F01/F02) — dish name + quantity extraction."""

import re
from dataclasses import dataclass, field


@dataclass
class ParsedLine:
    raw: str
    dish_name: str | None = None
    quantity: int = 1
    matched: bool = False
    dish_id: str | None = None
    unit_price: float | None = None
    prep_time_min: int | None = None


@dataclass
class ParseResult:
    lines: list[ParsedLine] = field(default_factory=list)
    special_notes: list[str] = field(default_factory=list)

    @property
    def matched_items(self) -> list[ParsedLine]:
        return [ln for ln in self.lines if ln.matched]

    @property
    def unmatched_lines(self) -> list[str]:
        return [ln.raw for ln in self.lines if not ln.matched]


NOTE_PREFIXES = ("no ", "without ", "extra ", "less ", "note:", "please ")

# qty name | name x qty | Nx name
QTY_PATTERNS = [
    re.compile(r"^(\d+)\s*[xX×]?\s+(.+)$"),
    re.compile(r"^(.+?)\s+[xX×]\s*(\d+)$"),
    re.compile(r"^(\d+)\s+(.+)$"),
]


def _normalize(text: str) -> str:
    return " ".join(text.strip().lower().split())


def _extract_qty_and_name(segment: str) -> tuple[int, str] | None:
    segment = segment.strip()
    if not segment:
        return None
    for pattern in QTY_PATTERNS:
        m = pattern.match(segment)
        if m:
            if pattern.pattern.startswith("^(.+?)"):
                return int(m.group(2)), m.group(1).strip()
            return int(m.group(1)), m.group(2).strip()
    return 1, segment


def _is_note(line: str) -> bool:
    lower = line.lower().strip()
    return any(lower.startswith(p) for p in NOTE_PREFIXES)


def parse_message_text(text: str) -> ParseResult:
    """Split message into lines and extract quantity + dish name candidates."""
    result = ParseResult()
    for raw_line in text.replace(",", "\n").split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        if _is_note(line):
            result.special_notes.append(line)
            continue
        extracted = _extract_qty_and_name(line)
        if not extracted:
            continue
        qty, name = extracted
        if qty < 1 or qty > 99:
            result.lines.append(ParsedLine(raw=line, dish_name=name, quantity=qty))
        else:
            result.lines.append(ParsedLine(raw=line, dish_name=name, quantity=qty))
    return result


def match_dishes(
    parsed: ParseResult,
    menu: list[dict],
) -> ParseResult:
    """Match parsed lines against kitchen menu [{id, name, price, prep_time_min}]."""
    menu_by_name = {_normalize(d["name"]): d for d in menu}
    for line in parsed.lines:
        if not line.dish_name:
            continue
        key = _normalize(line.dish_name)
        dish = menu_by_name.get(key)
        if not dish:
            for name_key, candidate in menu_by_name.items():
                if key in name_key or name_key in key:
                    dish = candidate
                    break
        if dish:
            line.matched = True
            line.dish_id = str(dish["id"])
            line.unit_price = float(dish["price"])
            line.prep_time_min = int(dish.get("prep_time_min", 30))
            line.dish_name = dish["name"]
    return parsed
