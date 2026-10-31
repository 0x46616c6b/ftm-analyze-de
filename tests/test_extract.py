from ftm_analyze_de.extract import extract_german
from ftm_analyze_de.extract.addresses import Address, find_addresses
from ftm_analyze_de.extract.identifiers import RegisterEntry, _vat_valid, find_register_entries, find_vat_ids
from ftm_analyze_de.extract.orgs import find_organizations, find_public_bodies, is_plausible_name
from ftm_analyze_de.extract.persons import find_persons
from ftm_analyze_de.extract.phones import find_phones

IMPRINT = """\
Impressum
Beispiel Verlag GmbH
Hauptstraße 5a
01067 Dresden
Telefon: 0351 4567890
Fax: (0351) 4567-891
E-Mail: info@example.org
Geschäftsführer: Dr. Max Mustermann
Registergericht: Amtsgericht Dresden, HRB 12345
USt-IdNr.: DE{vat}
"""


def _vat(prefix: str) -> str:
    """Complete eight digits with a valid check digit."""
    return next(prefix + str(d) for d in range(10) if _vat_valid(prefix + str(d)))


class TestOrganizations:
    def test_legal_forms(self):
        text = (
            "Der Verein Ein Prozent e.V. ruft auf. Die Beispiel Verlag GmbH & Co. KG liefert, "
            "ebenso Muster und Söhne UG (haftungsbeschränkt) sowie die Nord eG."
        )
        assert find_organizations(text) == {
            "Ein Prozent e.V.",
            "Beispiel Verlag GmbH & Co. KG",
            "Muster und Söhne UG (haftungsbeschränkt)",
            "Nord eG",
        }

    def test_more_legal_forms(self):
        text = "Die Muster SE & Co. KGaA, die Alpen GesmbH, die Bertelsmann Stiftung, Hans Meier e.Kfm."
        assert find_organizations(text) == {
            "Muster SE & Co. KGaA",
            "Alpen GesmbH",
            "Bertelsmann Stiftung",
            "Hans Meier e.Kfm.",
        }

    def test_spaced_form_normalized(self):
        assert find_organizations("Verein Beispielring e. V.") == {"Beispielring e.V."}

    def test_no_name_before_form(self):
        assert find_organizations("Das ist eine GmbH.") == set()

    def test_lowercase_se_not_matched(self):
        assert find_organizations("Das ist wirklich sehr gut") == set()

    def test_paragraph_reference_is_not_an_organization(self):
        assert find_organizations("nach § 54 Abs. 1 Satz 2 GmbH") == set()

    def test_short_fragment_is_not_an_organization(self):
        assert find_organizations("Frau E SE") == set()

    def test_plausible_name(self):
        assert is_plausible_name("Ein Prozent e.V.")
        assert is_plausible_name("BASF")
        assert not is_plausible_name("gemeinschaft")
        assert not is_plausible_name("Satz 2 GmbH")
        assert not is_plausible_name("GmbH")


class TestPublicBodies:
    def test_courts_and_authorities(self):
        text = (
            "Das Amtsgericht Dresden verwies an die Staatsanwaltschaft Leipzig. "
            "Laut Beschluss des Landgerichts Chemnitz und des Finanzamts Dresden-Nord ..."
        )
        assert find_public_bodies(text) == {
            "Amtsgericht Dresden",
            "Staatsanwaltschaft Leipzig",
            "Landgericht Chemnitz",
            "Finanzamt Dresden-Nord",
        }

    def test_complement(self):
        text = (
            "Das Bundesministerium für Wirtschaft und Klimaschutz hat dem Landesamt für "
            "Verfassungsschutz Sachsen geantwortet, ebenso das Bundesministerium der Justiz."
        )
        assert find_public_bodies(text) == {
            "Bundesministerium für Wirtschaft und Klimaschutz",
            "Landesamt für Verfassungsschutz Sachsen",
            "Bundesministerium der Justiz",
        }

    def test_federal(self):
        assert find_public_bodies("Der Bundesgerichtshof und das Bundeskriminalamt") == {
            "Bundesgerichtshof",
            "Bundeskriminalamt",
        }

    def test_article_is_not_a_place(self):
        assert find_public_bodies("beim Amtsgericht Die Akte") == set()


class TestAddresses:
    def test_variants(self):
        text = "Sitz: Töpferstr. 12, 02797 Kurort Oybin.\nHauptstraße 5a 01067 Dresden\nAm Markt 7"
        assert find_addresses(text) == {
            Address("Töpferstr.", "12", "02797", "Kurort Oybin"),
            Address("Hauptstraße", "5a", "01067", "Dresden"),
        }

    def test_preposition_streets_and_postbox(self):
        text = "Am Markt 7, 04109 Leipzig. Unter den Linden 1, 10117 Berlin. Postfach 100123, 01071 Dresden"
        assert find_addresses(text) == {
            Address("Am Markt", "7", "04109", "Leipzig"),
            Address("Unter den Linden", "1", "10117", "Berlin"),
            Address("Postfach", "100123", "01071", "Dresden"),
        }

    def test_no_street(self):
        assert find_addresses("Kapital 25000 EUR, 01067 Dresden") == set()

    def test_court_address_is_skipped(self):
        assert find_addresses("Gerichtsstraße 2, 09112 Chemnitz") == set()
        found = find_addresses("in den Amtsräumen Bäckerstraße 3, 04720 Döbeln")
        assert {a.street for a in found} == {"Bäckerstraße"}


class TestPersons:
    def test_titles(self):
        text = "Herr Max Mustermann und Frau Dr. Erika von Beispiel sowie Prof. Dr. Hans Schmidt."
        assert find_persons(text) == {"Max Mustermann", "Erika von Beispiel", "Hans Schmidt"}

    def test_offices(self):
        text = (
            "Oberbürgermeisterin Anna Muster und Rechtsanwalt Karl-Heinz Beispiel trafen "
            "Herrn Karl-Theodor von und zu Guttenberg."
        )
        assert find_persons(text) == {"Anna Muster", "Karl-Heinz Beispiel", "Karl-Theodor von und zu Guttenberg"}

    def test_and_is_not_a_particle(self):
        assert find_persons("Herr Max und Erika") == set()

    def test_register_style(self):
        assert find_persons("Vorstand: Mustermann, Max, Dresden, *26.01.1973") == {"Max Mustermann"}

    def test_none(self):
        assert find_persons("Frau Meier kommt später.") == set()


class TestPhones:
    def test_national_numbers(self):
        text = "Tel. 0351 4567890, Fax (030) 1234-5678, mobil 0171/1234567"
        assert find_phones(text) == ["+493514567890", "+493012345678", "+491711234567"]

    def test_international(self):
        assert find_phones("+49 (0)351 4567890 oder 0043 1 5123456") == ["+493514567890", "+4315123456"]

    def test_dates_and_amounts_are_no_numbers(self):
        assert find_phones("geboren am 26.01.1973, Kapital 25.000,00 EUR, PLZ 01067") == []


class TestIdentifiers:
    def test_vat(self):
        valid = _vat("12345678")
        invalid = valid[:-1] + str((int(valid[-1]) + 1) % 10)
        assert find_vat_ids(f"USt-IdNr. DE {valid[:3]} {valid[3:6]} {valid[6:]}, falsch DE{invalid}") == {f"DE{valid}"}

    def test_register_entry_with_court_and_org(self):
        text = "Beispiel Verlag GmbH, Sitz Dresden, Amtsgericht Dresden HRB 12345"
        assert find_register_entries(text) == {
            RegisterEntry("HRB 12345", "Amtsgericht Dresden", "Beispiel Verlag GmbH")
        }

    def test_court_after_number(self):
        text = "Muster e.V., eingetragen unter VR 4711 beim Amtsgericht Leipzig"
        assert find_register_entries(text) == {RegisterEntry("VR 4711", "Amtsgericht Leipzig", "Muster e.V.")}

    def test_ag_legal_form_is_not_a_court(self):
        assert find_register_entries("Muster AG HRB 99") == {RegisterEntry("HRB 99", None, "Muster AG")}


class TestFindings:
    def test_imprint(self):
        vat = _vat("81234567")
        findings = extract_german(IMPRINT.format(vat=vat))
        assert findings.organizations == {"Beispiel Verlag GmbH"}
        assert findings.persons == {"Max Mustermann"}
        assert findings.addresses == {Address("Hauptstraße", "5a", "01067", "Dresden")}
        assert findings.vat_ids == {f"DE{vat}"}
        assert findings.register_entries == {RegisterEntry("HRB 12345", "Amtsgericht Dresden", "Beispiel Verlag GmbH")}
        assert "Amtsgericht Dresden" in findings.public_bodies
