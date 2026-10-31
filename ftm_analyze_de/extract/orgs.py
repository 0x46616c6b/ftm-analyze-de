"""
Organizations in German text: names ending in a legal form (`Beispiel GmbH`)
and public bodies named by their head noun (`Amtsgericht Dresden`,
`Bundesministerium für Justiz`). The statistical NER model misses many of them.
"""

import re

from ftm_analyze_de.normalize import collapse

# longest first, the alternation stops at the first match
LEGAL_FORMS = (
    r"(?:GmbH|AG|SE|UG\s*\(haftungsbeschränkt\)|Ltd\.?|B\.\s?V\.)\s*&\s*Co\.?\s*(?:KGaA|KG|OHG)",
    r"gUG\s*\(haftungsbeschränkt\)",
    r"UG\s*\(haftungsbeschränkt\)",
    r"Ges\.?\s*m\.?\s*b\.?\s*H\.",
    r"PartG\s*mbB",
    r"e\.\s?Kfm\.",
    r"e\.\s?Kfr\.",
    r"e\.\s?V\.",
    r"e\.\s?K\.",
    r"e\.\s?G\.",
    r"gGmbH",
    r"GesmbH",
    r"GmbH",
    r"mbH",
    r"gAG",
    r"KGaA",
    r"VVaG",
    r"InvAG",
    r"PartG",
    r"AöR",
    r"KdöR",
    r"OHG",
    r"GbR",
    r"gUG",
    r"AG",
    r"KG",
    r"eG",
    r"SE",
    r"UG",
    r"Stiftung",
)
LEGAL_RE = re.compile(r"(?<![\w.])(?P<form>" + "|".join(LEGAL_FORMS) + r")(?![\w])")

_CONNECTORS = {"und", "für", "fuer", "der", "des", "die", "de", "von", "zur", "zum", "&", "+"}
# Words in front of a name that are not part of it
_LEADING_STOP = {
    "der", "die", "das", "dem", "den", "des",
    "verein", "firma", "unternehmen", "gesellschaft", "bei", "von", "vom", "an",
    "im", "in", "zu", "zur", "zum", "mit", "für", "und", "oder", "auf", "aus",
    "herr", "frau", "dr.", "prof.", "gegen", "durch", "sowie",
    "satz", "abs.", "gründung", "eintragung", "umwandlung",
}  # fmt: skip
# capitalised word, or a number glued to letters (`7sections`), never a bare number
_NAME_TOKEN_RE = re.compile(r"^(?:[A-ZÄÖÜ]|\d+(?=[A-Za-zÄÖÜäöüß]))[\wäöüßÄÖÜ&'\-\.]*$")
_WORD_MIN = 3  # a name needs one token with this many characters
_BREAK_RE = re.compile(r"[\n;:!?|()\[\]\"„“«»]|(?<=[a-zäöüß]{3})\.\s|,\s")
MAX_NAME_TOKENS = 6

# Head nouns of public bodies. Optional genitive ending (`des Amtsgerichts`) is dropped.
_COURTS = (
    r"Amtsgericht|Landgericht|Oberlandesgericht|Verwaltungsgericht|Oberverwaltungsgericht|"
    r"Sozialgericht|Landessozialgericht|Arbeitsgericht|Landesarbeitsgericht|Finanzgericht|"
    r"Verfassungsgerichtshof|Staatsgerichtshof"
)
_LOCAL_BODIES = (
    rf"{_COURTS}|Generalstaatsanwaltschaft|Staatsanwaltschaft|Landratsamt|Finanzamt|"
    r"Polizeidirektion|Polizeipräsidium|Polizeiinspektion|Polizeirevier|Stadtverwaltung|"
    r"Gemeindeverwaltung|Kreisverwaltung|Bezirksamt|Ordnungsamt|Jobcenter|Landeskriminalamt|"
    r"Stadtrat|Kreistag|Landtag|Regierungspräsidium|Bezirksregierung|Landesdirektion"
)
# named by a `für/der/des …` complement
_COMPLEMENT_BODIES = (
    r"Bundesministerium|Staatsministerium|Landesministerium|Ministerium|Bundesamt|Landesamt|"
    r"Bundesanstalt|Landesanstalt|Bundeszentrale|Landeszentrale|Bundesagentur|Senatsverwaltung|"
    r"Behörde|Amt|Beauftragte[rn]?"
)
# unique bodies without a further name
_FEDERAL_BODIES = (
    r"Bundesgerichtshof|Bundesverfassungsgericht|Bundesverwaltungsgericht|Bundesfinanzhof|"
    r"Bundessozialgericht|Bundesarbeitsgericht|Bundespatentgericht|Bundeskriminalamt|"
    r"Bundesnachrichtendienst|Bundeskanzleramt|Bundespräsidialamt|Bundesrechnungshof|"
    r"Bundestag|Bundesrat|Bundespolizei|Bundesanwaltschaft|Generalbundesanwalt|Bundeswehr|"
    r"Militärischer Abschirmdienst|Zollkriminalamt"
)
_GEN = r"(?:e?s)?"
_PLACE = r"[A-ZÄÖÜ][\wäöüß]+(?:-[A-ZÄÖÜ][\wäöüß]+)*"
# the head may be declined: `des Amtsgerichts Dresden`. The complement is a
# lookahead, so a body named inside it is still found.
_PUBLIC_RE = re.compile(
    rf"\b(?P<local>{_LOCAL_BODIES}){_GEN}\s+(?P<place>{_PLACE}(?:\s+(?:Land|Stadt|Nord|Süd|Ost|West|Mitte))?)"
    rf"|\b(?P<head>{_COMPLEMENT_BODIES}){_GEN}\s+(?P<link>für|der|des)\s+(?=(?P<rest>[A-ZÄÖÜ][^\n.;:,()]{{2,120}}))"
    rf"|\b(?P<federal>{_FEDERAL_BODIES}){_GEN}\b"
)
_COMPLEMENT_LINK = {"und", "für", "der", "des", "die", "den", "dem", "von", "im", "in", "sowie", "-"}
# capitalised words after a court that are not a place
_NOT_A_PLACE = {"Der", "Die", "Das", "Den", "Dem", "Des", "Ein", "Eine", "Am", "Im", "In", "Mit", "Hat", "Ist"}


def _normalize_form(form: str) -> str:
    form = collapse(form)
    return re.sub(r"\be\.\s(?=(?:[VKG]|Kf[mr])\.)", "e.", form)


def find_organizations(text: str) -> set[str]:
    """Names ending in a German legal form, e.g. `Ein Prozent e.V.`"""
    found: set[str] = set()
    for match in LEGAL_RE.finditer(text):
        prefix = text[max(0, match.start() - 120) : match.start()]
        # only the text after the last sentence/clause break belongs to the name
        breaks = list(_BREAK_RE.finditer(prefix))
        if breaks:
            prefix = prefix[breaks[-1].end() :]
        tokens: list[str] = []
        for token in reversed(prefix.split()):
            if _NAME_TOKEN_RE.match(token) or (tokens and token.lower() in _CONNECTORS):
                tokens.append(token)
                if len(tokens) >= MAX_NAME_TOKENS:
                    break
            else:
                break
        tokens.reverse()
        while tokens and tokens[0].lower() in _LEADING_STOP | _CONNECTORS:
            tokens.pop(0)
        if tokens and tokens[-1].lower() in _CONNECTORS:
            tokens.pop()
        if not tokens or not any(len(t.strip(".&+-")) >= _WORD_MIN for t in tokens):
            continue
        found.add(f"{' '.join(tokens)} {_normalize_form(match.group('form'))}")
    return found


def _complement(rest: str) -> str | None:
    """`Wirtschaft und Klimaschutz hat …` -> `Wirtschaft und Klimaschutz`"""
    tokens: list[str] = []
    for token in rest.split():
        if token[0].isupper() or token in _COMPLEMENT_LINK or (tokens and token[0] == "-"):
            tokens.append(token)
        else:
            break
    while tokens and tokens[-1] in _COMPLEMENT_LINK:
        tokens.pop()
    return " ".join(tokens) or None


def find_public_bodies(text: str) -> set[str]:
    """Courts, ministries, authorities, e.g. `Amtsgericht Dresden`, `Bundesamt für Justiz`"""
    found: set[str] = set()
    for match in _PUBLIC_RE.finditer(text):
        if match.group("local"):
            place = match.group("place")
            if place.split()[0] in _NOT_A_PLACE:
                continue
            found.add(f"{match.group('local')} {place}")
        elif match.group("head"):
            if complement := _complement(match.group("rest")):
                found.add(f"{match.group('head')} {match.group('link')} {complement}")
        else:
            found.add(match.group("federal"))
    return found


_MENTION_JUNK_RE = re.compile(r"§|\bAbs\.|\bSatz\b|\bArt\.|^\d+\s")


def is_plausible_name(name: str) -> bool:
    """Reject NER noise: lower-case fragments, paragraph references, bare legal forms."""
    name = collapse(name)
    if len(name) < 4 or not (name[0].isupper() or name[0].isdigit()):
        return False
    if _MENTION_JUNK_RE.search(name):
        return False
    return not LEGAL_RE.fullmatch(name)
