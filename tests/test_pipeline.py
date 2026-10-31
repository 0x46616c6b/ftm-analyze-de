"""Runs the full pipeline, needs ftm-analyze with its models (test stage of the Dockerfile)."""

import pytest

pytest.importorskip("ftm_analyze")

from followthemoney import model  # noqa: E402

from ftm_analyze_de.pipeline import analyze_entity_de  # noqa: E402

TEXT = """\
Impressum
Beispiel Verlag GmbH
Hauptstraße 5a
01067 Dresden
Telefon: 0351 4567890
E-Mail: info@example.org
Geschäftsführer: Dr. Max Mustermann
Registergericht: Amtsgericht Dresden, HRB 12345

Die Geschäfts-
führung traf sich mit Angela Merkel in Dresden.
"""

REGISTER_PAGE = """\
Handelsregister B des                                            Nummer der Firma:
Amtsgerichts Dresden            Wiedergabe des aktuellen                       HRB 4711
                                           Registerinhalts
2.     a) Firma:
     Beispiel GmbH
      b) Sitz, Niederlassung, inländische Geschäftsanschrift, empfangsberechtigte Person, Zweigniederlassungen:
     Dresden
     Geschäftsanschrift: Hauptstr. 12, 01067 Dresden
4.     b) Vertretungsberechtigte und besondere Vertretungsbefugnis:
      Geschäftsführer: Muster, Klaus, Radeberg, *17.12.1977
"""


def _document(text: str, schema: str = "PlainText"):
    entity = model.make_entity(schema)
    entity.id = "doc-1"
    entity.add("bodyText", text) if schema == "PlainText" else entity.add("indexText", text)
    return entity


def _by_schema(results, schema):
    return [r for r in results if r.schema.name == schema]


def test_compat_applied():
    from ftm_analyze.analysis import patterns
    from ftm_analyze.analysis.extract import base

    assert base.NAME_MIN_LENGTH == 3
    assert all(not hasattr(p, "pattern") or "\\d" not in p.pattern for p in patterns.REGEX_TYPES if p)


def test_imprint():
    results, register = analyze_entity_de(_document(TEXT))
    assert register == []
    doc = next(r for r in results if r.id == "doc-1")
    assert "+493514567890" in doc.get("phoneMentioned")
    assert "info@example.org" in doc.get("emailMentioned")
    assert "Beispiel Verlag GmbH" in doc.get("companiesMentioned")
    assert "Max Mustermann" in doc.get("peopleMentioned")

    names = {r.first("name") for r in _by_schema(results, "Mention")}
    assert {"Beispiel Verlag GmbH", "Max Mustermann", "Amtsgericht Dresden"} <= names
    assert "amtsgericht dresden" not in {v.lower() for v in doc.get("locationMentioned")}

    (address,) = _by_schema(results, "Address")
    assert address.first("full") == "Hauptstraße 5a, 01067 Dresden"

    (company,) = _by_schema(results, "Company")
    assert company.first("registrationNumber") == "HRB 12345"
    assert company.first("name") == "Beispiel Verlag GmbH"


def test_short_names_pass_the_length_filter():
    # upstream drops names under 8 characters; single words may still be dropped
    # afterwards by upstream's fastText type model (e.g. `Dresden` as trash)
    from ftm_analyze.analysis.extract import test_name

    assert test_name("Bosch")
    assert test_name("BASF")
    assert not test_name("AG")


def test_register_page_is_detected():
    results, register = analyze_entity_de(_document(REGISTER_PAGE, "Pages"))
    org = next(r for r in register if r.schema.name == "Company")
    assert org.first("name") == "Beispiel GmbH"
    assert org.first("registrationNumber") == "HRB 4711"
    assert {r.schema.name for r in register} == {"Company", "Person", "Directorship"}


def test_tasks_register_legacy_names():
    from ftm_analyze_de import tasks

    assert {
        "ftm_analyze_de.tasks.analyze",
        "ftm_analyze.tasks.analyze",
        "hr_analyze.tasks.analyze",
    } <= set(tasks.app.tasks)
