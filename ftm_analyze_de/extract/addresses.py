"""German postal addresses: `Straße Nr, PLZ Ort` and `Postfach Nr, PLZ Ort`."""

import re
from dataclasses import dataclass

from ftm_analyze_de.normalize import collapse

# Prefix words in front of a street, and streets that belong to authorities
_STREET_NOISE = {"amtsräumen", "geschäftsräumen", "räumen", "büroräumen", "anschrift", "sitz"}
_AUTHORITY_STREET_RE = re.compile(r"gericht", re.IGNORECASE)

_STREET_SUFFIX = r"straße|strasse|str\.|weg|allee|platz|gasse|ring|damm|ufer|chaussee|pfad|markt|steig|hof|park"
# `Am Markt`, `An der Kirche`, `Unter den Linden`
_STREET_PREPOSITION = (
    r"(?:Am|An der|An den|An dem|Auf der|Auf dem|Im|In der|In den|Zum|Zur|Unter den|Hinter der|Hinter dem|Vor dem)"
)
_STREET = (
    rf"(?:[A-ZÄÖÜ][\wäöüß\-]*[ \-])?[A-ZÄÖÜ][\wäöüß\-]*?(?:{_STREET_SUFFIX})"
    rf"|{_STREET_PREPOSITION}\s+[A-ZÄÖÜ][\wäöüß\-]+"
    r"|Postfach"
)
ADDRESS_RE = re.compile(
    rf"(?P<street>{_STREET})"
    r"\s+(?P<nr>\d{1,6}\s?[a-zA-Z]?(?:\s?[-/]\s?\d{1,4}\s?[a-zA-Z]?)?)"
    r"\s*[,\n]?\s*(?:D-)?(?P<plz>\d{5})\s+"
    r"(?P<city>[A-ZÄÖÜ][\wäöüß\-]+(?:[ \-][A-ZÄÖÜ][\wäöüß\-]+)?)"
)


@dataclass(frozen=True)
class Address:
    street: str
    number: str
    postal_code: str
    city: str

    @property
    def full(self) -> str:
        return f"{self.street} {self.number}, {self.postal_code} {self.city}"


def find_addresses(text: str) -> set[Address]:
    """German postal addresses: `Straße Nr, PLZ Ort`"""
    found: set[Address] = set()
    for match in ADDRESS_RE.finditer(text):
        street = collapse(match.group("street"))
        first, _, rest = street.partition(" ")
        if rest and first.lower() in _STREET_NOISE:
            street = rest
        if _AUTHORITY_STREET_RE.search(street):
            continue  # court addresses from letterheads, not relevant to the content
        found.add(
            Address(
                street=street,
                number=collapse(match.group("nr")),
                postal_code=match.group("plz"),
                city=collapse(match.group("city")).rstrip("."),
            )
        )
    return found
