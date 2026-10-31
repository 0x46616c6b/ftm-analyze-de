"""
Person names in German text, anchored on a salutation, academic title or
office (`Frau Dr. Erika Muster`, `Oberbürgermeister Max Muster`) and on the
register notation `Nachname, Vorname, Ort, *Datum`.
"""

import re

from ftm_analyze_de.extract.register import parse_persons

_ACADEMIC = (
    r"(?:Dr\.(?:\s?(?:med|jur|phil|rer\.\s?nat|rer\.\s?pol|h\.\s?c|ing|-Ing)\.)?|Prof\.|Dipl\.-[A-Za-zäöü.]+|Mag\.)"
)
_OFFICES = (
    r"Herrn?|Frau|"
    r"Rechtsanwalt|Rechtsanwältin|RA|RAin|Notar(?:in)?|Steuerberater(?:in)?|"
    r"Richter(?:in)?|Staatsanwalt|Staatsanwältin|Oberstaatsanwalt|Oberstaatsanwältin|"
    r"Oberbürgermeister(?:in)?|Bürgermeister(?:in)?|Landrat|Landrätin|"
    r"Bundesminister(?:in)?|Staatsminister(?:in)?|Minister(?:in)?|Ministerpräsident(?:in)?|"
    r"Staatssekretär(?:in)?|Abgeordnete[rn]?|Stadtrat|Stadträtin|"
    r"Geschäftsführer(?:in)?|Vorsitzende[rn]?|Vorstand|Prokurist(?:in)?|Inhaber(?:in)?"
)
_FIRST = r"[A-ZÄÖÜ][a-zäöüß]+(?:-[A-ZÄÖÜ][a-zäöüß]+)?"
_PARTICLES = r"(?:(?:von und zu|von der|von den|von dem|van der|van den|von|van|de|zu|vom|zur)\s+)?"
_LAST = rf"{_PARTICLES}[A-ZÄÖÜ][a-zäöüß]+(?:-[A-ZÄÖÜ][a-zäöüß]+)?"
_PERSON_RE = re.compile(
    rf"\b(?:(?:{_OFFICES})\s+(?:{_ACADEMIC}\s*)*|{_ACADEMIC}(?:\s*{_ACADEMIC})*\s+)"
    rf"(?P<first>{_FIRST})\s+(?P<last>{_LAST})\b"
)
# first names that are really the start of a phrase: `Frau Kollegin Muster`
_NOT_A_FIRST_NAME = {
    "Kollege", "Kollegin", "Vorsitzende", "Vorsitzender", "Präsident", "Präsidentin",
    "Abgeordnete", "Abgeordneter", "Minister", "Ministerin", "Doktor", "Professor",
}  # fmt: skip


def find_persons(text: str) -> set[str]:
    """`Herr/Frau/Dr./office Vorname Nachname` and register style `Nachname, Vorname, Ort, *Datum`"""
    found: set[str] = set()
    for match in _PERSON_RE.finditer(text):
        first, last = match.group("first"), match.group("last")
        if first in _NOT_A_FIRST_NAME:
            continue
        found.add(f"{first} {last}")
    for person in parse_persons(text):
        found.add(f"{person.first_name} {person.last_name}")
    return found
