"""Text and name normalisation for German documents."""

import re

_HYPHEN_BREAK_RE = re.compile(r"(?<=[A-Za-zÄÖÜäöüß])-[ \t]*\r?\n[ \t]*(?=[a-zäöüß])")
_FOLD = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


def collapse(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def repair_hyphenation(text: str) -> str:
    """
    Join words split at a line end, as OCR and PDF text keep them:
    `Geschäfts-\\nführer` -> `Geschäftsführer`. A capitalised continuation
    (`Sachsen-\\nAnhalt`) is a real hyphenated compound and stays untouched.
    """
    return _HYPHEN_BREAK_RE.sub("", text)


def fold(value: str) -> str:
    """Comparison key that treats `Müller` and `Mueller` as the same name."""
    return collapse(value).lower().translate(_FOLD)


def dedupe(values: set[str]) -> set[str]:
    """Keep one spelling per folded key, preferring the one with umlauts."""
    picked: dict[str, str] = {}
    for value in sorted(values):
        key = fold(value)
        current = picked.get(key)
        if current is None or len(value) < len(current):
            picked[key] = value
    return set(picked.values())
