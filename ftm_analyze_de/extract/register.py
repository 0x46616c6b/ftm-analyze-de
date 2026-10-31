"""
Parse German commercial / association register printouts (Handelsregister,
Vereinsregister) from plain page text.

Pure functions, no OpenAleph dependencies, so they are testable on their own.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass, field

LEGAL_FORMS = r"e\.\s?V\.|gGmbH|GmbH(?: & Co\. KG)?|UG \(haftungsbeschränkt\)|mbH|AG|KG|OHG|eG|SE|e\.\s?K\."

# number sits in the page header, sometimes on the line below its label
REGISTER_RE = re.compile(r"\b((?:HRA|HRB|VR|GnR|PR)\s?\d+(?:\s?[A-Z]{1,2})?)\b")
HEADER_CHARS = 600
HEADER_LABEL_RE = re.compile(r"Nummer\s+(?:der|des)\s+(?:Firma|Vereins|Genossenschaft|Partnerschaft)")
COURT_RE = re.compile(r"Amtsgerichts?\s+([A-ZÄÖÜ][\wäöüß.\- ]*?)(?=\s{2,}|\n|$)")
NAME_RE = re.compile(
    r"a\)\s*(?:Name|Firma):\s*(?P<name>.+?)\s*b\)\s*Sitz[^:]*:\s*(?P<seat>[^\n]+)",
    re.DOTALL,
)
NAME_FALLBACK_RE = re.compile(rf"([^\n|]{{2,80}}?(?:{LEGAL_FORMS}))(?=\s{{2,}}|\n|$)")
ADDRESS_LABEL = "Geschäftsanschrift"
ADDRESS_WINDOW = 600
# `Straße Nr, PLZ Ort` as one table cell
POSTAL_RE = re.compile(r"^.+?\s\d+\s?[a-zA-Z]?(?:\s?[-/]\s?\d+\s?[a-zA-Z]?)?,\s*\d{5}\s+\S.*$")
SEAT_RE = re.compile(r"[A-ZÄÖÜ][^\d:,]{1,50}")
_ROLES = (
    r"(?:Stellvertretende[rn]?\s+)?Vorsitzende[rn]?|Vorstand|Notvorstand|Geschäftsführer(?:in)?|"
    r"Notgeschäftsführer(?:in)?|Liquidator(?:in)?|Prokurist(?:in)?|Kassenwart|Kassierer(?:in)?|"
    r"Schatzmeister(?:in)?|Schriftführer(?:in)?|Beisitzer(?:in)?|Inhaber(?:in)?|"
    r"Persönlich haftende[rn]? Gesellschafter(?:in)?|Gesellschafter(?:in)?"
)
ROLE_RE = re.compile(rf"(?:^|\s)({_ROLES})$")
CAPITAL_RE = re.compile(r"Stammkapital:?\s*\n?\s*([\d.,]+\s*EUR)")

_NAME_TOKEN = r"[A-ZÄÖÜ][\wäöüßÄÖÜ'\-]*"
_NAME_PART = rf"(?:(?:von|van|de|zu|der|den|vom|zur|Graf|Freiherr)\s+)*{_NAME_TOKEN}(?:[ \-]{_NAME_TOKEN}){{0,2}}"
PERSON_RE = re.compile(
    rf"(?:(?P<role>[A-ZÄÖÜ][\wäöüß\-/ ]{{2,40}}?):\s+)?"
    rf"(?P<last>{_NAME_PART}),\s*(?P<first>{_NAME_PART}),\s*"
    rf"(?P<city>[A-ZÄÖÜ][^,\n*]{{1,60}}?),\s*\*(?P<dob>\d{{2}}\.\d{{2}}\.\d{{4}})"
)


@dataclass(frozen=True)
class Person:
    last_name: str
    first_name: str
    city: str
    birth_date: str  # ISO
    role: str | None = None


@dataclass
class Register:
    number: str | None = None
    court: str | None = None
    name: str | None = None
    seat: str | None = None
    address: str | None = None
    capital: str | None = None
    persons: list[Person] = field(default_factory=list)

    @property
    def is_company(self) -> bool:
        return bool(self.number and self.number.startswith(("HRA", "HRB")))


def _collapse(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _clean_name(value: str) -> str | None:
    """Collapse whitespace, normalise `e. V.` to `e.V.`, reject bare legal forms."""
    name = re.sub(r"\be\.\s+([VKG])\.", r"e.\1.", _collapse(value))
    return None if re.fullmatch(LEGAL_FORMS, name) else name


def _clean_role(role: str | None) -> str | None:
    """Keep only known office names; labels like `Ausgeschieden` are not roles."""
    if role and (m := ROLE_RE.search(_collapse(role))):
        return m.group(1)
    return None


def _clean_seat(seat: str | None) -> str | None:
    seat = _collapse(seat or "")
    return seat if SEAT_RE.fullmatch(seat) else None


def _find_address(text: str) -> str | None:
    """First `Straße Nr, PLZ Ort` cell shortly after the `Geschäftsanschrift` label."""
    start = text.find(ADDRESS_LABEL)
    if start < 0:
        return None
    for line in text[start : start + ADDRESS_WINDOW].splitlines():
        for cell in re.split(r"\s{2,}", line.strip()):
            cell = _collapse(re.sub(rf"^{ADDRESS_LABEL}:?\s*", "", cell))
            if POSTAL_RE.match(cell):
                return cell
    return None


def _find_seat(text: str) -> str | None:
    """Chronological printouts: the seat follows a lone `b)` cell in the first data row."""
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip() == "b)":
            for following in lines[index + 1 : index + 4]:
                if cell := re.split(r"\s{2,}", following.strip())[0]:
                    return _clean_seat(cell)
    return None


def _iso(date: str) -> str:
    day, month, year = date.split(".")
    return f"{year}-{month}-{day}"


def _fallback_name(text: str) -> str | None:
    """
    Find the company name in a multi-column (chronological) printout. When the
    name wraps, the legal form stands alone on a later line: join it with the
    last text line above it.
    """
    lines = text.splitlines()
    for index, line in enumerate(lines):
        for match in NAME_FALLBACK_RE.finditer(line):
            if name := _clean_name(match.group(1)):
                return name
            for previous in reversed(lines[max(0, index - 4) : index]):
                head = re.split(r"\s{2,}", previous.strip())[0]
                if not head:
                    continue
                if re.match(r"[A-ZÄÖÜ]", head) and not re.match(r"[A-Za-z]\)", head):
                    return _clean_name(f"{head} {_collapse(match.group(1))}")
                break
    return None


def parse_persons(text: str) -> list[Person]:
    """Find `Role: Last, First, City, *DD.MM.YYYY` lines, also inside table layouts."""
    persons: dict[tuple[str, str, str], Person] = {}
    for line in text.splitlines():
        for match in PERSON_RE.finditer(line):
            role = match.group("role")
            person = Person(
                last_name=_collapse(match.group("last")),
                first_name=_collapse(match.group("first")),
                city=_collapse(match.group("city")),
                birth_date=_iso(match.group("dob")),
                role=_clean_role(role),
            )
            key = (person.last_name, person.first_name, person.birth_date)
            if key not in persons or (person.role and not persons[key].role):
                persons[key] = person
    return list(persons.values())


def parse_register(text: str) -> Register:
    """Extract register header data, name/seat and persons from one page of text."""
    reg = Register(persons=parse_persons(text))
    header = text[:HEADER_CHARS]
    if HEADER_LABEL_RE.search(header) and (m := REGISTER_RE.search(header)):
        reg.number = _collapse(m.group(1))
    if m := COURT_RE.search(text):
        reg.court = f"Amtsgericht {_collapse(m.group(1))}"
    if m := NAME_RE.search(text):
        reg.name = _clean_name(m.group("name"))
        reg.seat = _clean_seat(m.group("seat"))
    if not reg.name and reg.number:
        # chronological printouts are multi-column tables without `Name:` label
        reg.name = _fallback_name(text)
        reg.seat = reg.seat or _find_seat(text)
    reg.address = _find_address(text)
    if m := CAPITAL_RE.search(text):
        reg.capital = _collapse(m.group(1))
    return reg


def is_register_page(text: str) -> bool:
    """Page header of a register printout: `Nummer der Firma: HRB 1234` or similar."""
    header = text[:HEADER_CHARS]
    return bool(HEADER_LABEL_RE.search(header) and REGISTER_RE.search(header))


def parse_document(texts: Iterable[str]) -> Register:
    """Merge the per-page results of all page texts of one document."""
    merged = Register()
    persons: dict[tuple[str, str, str], Person] = {}
    for text in texts:
        reg = parse_register(text)
        for attr in ("number", "court", "name", "seat", "address", "capital"):
            if not getattr(merged, attr) and getattr(reg, attr):
                setattr(merged, attr, getattr(reg, attr))
        for person in reg.persons:
            key = (person.last_name, person.first_name, person.birth_date)
            if key not in persons or (person.role and not persons[key].role):
                persons[key] = person
    merged.persons = list(persons.values())
    return merged
