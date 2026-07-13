"""Shared PDF helpers for Kitchcu document generators."""

ORANGE = (230, 81, 0)
DARK = (33, 33, 33)
GRAY = (97, 97, 97)
WHITE = (255, 255, 255)
LIGHT_BG = (250, 248, 245)
ACCENT = (0, 105, 92)
TEAL = (0, 121, 107)


def ascii_safe(text: str) -> str:
    """FPDF Helvetica is Latin-1 only; normalize Unicode to ASCII."""
    if not text:
        return text
    replacements = {
        "\u2014": " - ",
        "\u2013": "-",
        "\u2192": "->",
        "\u2022": "-",
        "\u2026": "...",
        "\u2265": ">=",
        "\u2264": "<=",
        "\u20b9": "Rs ",
        "\u201c": '"',
        "\u201d": '"',
        "\u2018": "'",
        "\u2019": "'",
        "\u2705": "[DONE]",
        "\u23f3": "[NEXT]",
        "\u1f7e1": "[PARTIAL]",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text.encode("ascii", "replace").decode("ascii")
