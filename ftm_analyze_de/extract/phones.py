"""
Phone numbers in national notation (`0351 123456`, `(030) 1234-56`), which
the upstream regex only accepts with a country prefix.
"""

import re

import phonenumbers
from phonenumbers import PhoneNumberFormat, PhoneNumberMatcher

# dates such as `26.01.1973` are no phone numbers
_DOTTED_DATE_RE = re.compile(r"\b\d{1,2}\.\d{1,2}\.\d{2,4}\b")


def find_phones(text: str, region: str = "DE") -> list[str]:
    """Valid numbers in E.164 format, national numbers are read in `region`."""
    found: list[str] = []
    for match in PhoneNumberMatcher(text, region):
        if _DOTTED_DATE_RE.fullmatch(match.raw_string.strip()):
            continue
        value = phonenumbers.format_number(match.number, PhoneNumberFormat.E164)
        if value not in found:
            found.append(value)
    return found


class _Match:
    def __init__(self, value: str):
        self.value = value

    def group(self, index: int = 0) -> str:
        return self.value


class PhonePattern:
    """Stands in for upstream's phone regex: `finditer` yields E.164 numbers."""

    def __init__(self, region: str = "DE"):
        self.region = region

    def finditer(self, text: str):
        for value in find_phones(text, self.region):
            yield _Match(value)
