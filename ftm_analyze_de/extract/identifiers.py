"""
German identifiers: VAT numbers (`USt-IdNr. DE123456789`) and register
entries (`Amtsgericht Dresden, HRB 12345`), linked to the organization named
right before them, as in a typical imprint.
"""

import re
from dataclasses import dataclass

from ftm_analyze_de.extract.orgs import find_organizations
from ftm_analyze_de.normalize import collapse

VAT_RE = re.compile(r"\bDE\s?(\d{3})\s?(\d{3})\s?(\d{3})\b")
REGISTER_NUMBER_RE = re.compile(r"\b(?P<kind>HRA|HRB|VR|GnR|PR|PartR)\s?(?P<nr>\d{1,6}(?:\s?[A-Z]{1,2}\b)?)")
_PLACE = r"[A-ZÄÖÜ][\wäöüß]+(?:[ \-](?:im|am|an der|in der)\s[A-ZÄÖÜ][\wäöüß]+|-[A-ZÄÖÜ][\wäöüß]+)?"
_COURT_RE = re.compile(rf"(?:Amtsgerichts?|Registergerichts?|AG)\s*:?\s+(?!Amtsgericht)(?P<place>{_PLACE})")
_NOT_A_COURT_PLACE = {"Amtsgericht", "Registergericht", "HRA", "HRB", "VR", "GnR", "PR", "PartR"}
# how far around a register number the court and the organization may stand
COURT_WINDOW = 80
ORG_WINDOW = 250


@dataclass(frozen=True)
class RegisterEntry:
    number: str  # `HRB 12345`
    court: str | None  # `Amtsgericht Dresden`
    organization: str | None


def _vat_valid(digits: str) -> bool:
    """ISO 7064 MOD 11,10 check digit of German VAT numbers."""
    product = 10
    for digit in digits[:8]:
        total = (int(digit) + product) % 10 or 10
        product = (2 * total) % 11
    check = 11 - product
    return (0 if check == 10 else check) == int(digits[8])


def find_vat_ids(text: str) -> set[str]:
    found: set[str] = set()
    for match in VAT_RE.finditer(text):
        digits = "".join(match.groups())
        if _vat_valid(digits):
            found.add(f"DE{digits}")
    return found


def _court(window: str) -> str | None:
    matches = list(_COURT_RE.finditer(window))
    if not matches:
        return None
    place = matches[-1].group("place")
    if place in _NOT_A_COURT_PLACE:
        return None
    return f"Amtsgericht {place}"


def find_register_entries(text: str) -> set[RegisterEntry]:
    found: set[RegisterEntry] = set()
    for match in REGISTER_NUMBER_RE.finditer(text):
        number = f"{match.group('kind')} {collapse(match.group('nr'))}"
        before = text[max(0, match.start() - COURT_WINDOW) : match.start()]
        after = text[match.end() : match.end() + COURT_WINDOW]
        court = _court(before) or _court(after.split("\n")[0])
        org_text = text[max(0, match.start() - ORG_WINDOW) : match.start()]
        orgs = find_organizations(org_text)
        # the name closest to the number
        organization = max(orgs, key=lambda o: org_text.rfind(o.split()[0])) if orgs else None
        found.add(RegisterEntry(number=number, court=court, organization=organization))
    return found
