import unittest

from ftm_analyze_de.extract.register import parse_document, parse_persons, parse_register

VEREIN_AD = """\
Vereinsregister des                                              Nummer des Vereins:
Amtsgerichts Musterstadt        Wiedergabe des aktuellen                       VR 1234
                                           Registerinhalts

2.     a) Name:

     Ein Prozent e.V.

      b) Sitz:

     Musterstadt

3.     b) Vertretungsberechtigte und besondere Vertretungsbefugnis:

      Vorstand: Mustermann, Max, Musterstadt, *26.01.1973
      Vorstand: von Beispiel, Erika-Maria, Dresden, *03.09.1965
"""

GMBH_AD = """\
Handelsregister B des                     Abteilung B                      Nummer der Firma:
Amtsgerichts Musterstadt        Wiedergabe des aktuellen                     HRB 4711
2.     a) Firma:
      Beispiel GmbH
      b) Sitz, Niederlassung, inländische Geschäftsanschrift, empfangsberechtigte Person, Zweigniederlassungen:
      Oybin
      Geschäftsanschrift: Hauptstr. 12, 02797 Kurort Oybin
3.    Grund- oder Stammkapital:
      25.000,00 EUR
      Geschäftsführer: Muster, Philip, Schkeuditz, *01.07.1991
"""

CD_TABLE = """\
Vereinsregister des Amtsgerichts Musterstadt     Abruf vom 29.06.2021    Nummer des Vereins:         VR 2740
    1       a)                                                                a)
              Beispielring Musterstadt e.V.                             Jeweils zwei Vorstandsmitglieder
                                                                        Vorsitzender:
                                                                      Muster, Klaus, Radeberg, *17.12.1977
"""


class ParserTest(unittest.TestCase):
    def test_verein(self):
        reg = parse_register(VEREIN_AD)
        self.assertEqual(reg.number, "VR 1234")
        self.assertEqual(reg.court, "Amtsgericht Musterstadt")
        self.assertEqual(reg.name, "Ein Prozent e.V.")
        self.assertEqual(reg.seat, "Musterstadt")
        self.assertFalse(reg.is_company)
        self.assertEqual(
            [(p.last_name, p.first_name, p.city, p.birth_date, p.role) for p in reg.persons],
            [
                ("Mustermann", "Max", "Musterstadt", "1973-01-26", "Vorstand"),
                ("von Beispiel", "Erika-Maria", "Dresden", "1965-09-03", "Vorstand"),
            ],
        )

    def test_gmbh(self):
        reg = parse_register(GMBH_AD)
        self.assertEqual(reg.number, "HRB 4711")
        self.assertEqual(reg.name, "Beispiel GmbH")
        self.assertEqual(reg.seat, "Oybin")
        self.assertEqual(reg.address, "Hauptstr. 12, 02797 Kurort Oybin")
        self.assertEqual(reg.capital, "25.000,00 EUR")
        self.assertTrue(reg.is_company)
        self.assertEqual(reg.persons[0].role, "Geschäftsführer")

    def test_chronological_table(self):
        reg = parse_register(CD_TABLE)
        self.assertEqual(reg.number, "VR 2740")
        self.assertEqual(reg.name, "Beispielring Musterstadt e.V.")
        self.assertEqual(len(reg.persons), 1)
        self.assertEqual(reg.persons[0].last_name, "Muster")

    def test_document_merges_pages(self):
        page2 = "Seite 2 von 2\n Geschäftsführer: Beispiel, Anna, Berlin, *02.02.1980\n Vorstand: VR 99 Nummer"
        reg = parse_document([page2, GMBH_AD])
        self.assertEqual(reg.number, "HRB 4711")
        self.assertEqual(reg.name, "Beispiel GmbH")
        self.assertEqual({p.last_name for p in reg.persons}, {"Beispiel", "Muster"})

    def test_number_needs_header_label(self):
        self.assertIsNone(parse_register("Seite 2\nsiehe VR 99").number)

    def test_no_false_positive(self):
        self.assertEqual(parse_persons("Rechnung, Nr. 5, Berlin, 12.05.2020"), [])


if __name__ == "__main__":
    unittest.main()


class CleanNameTest(unittest.TestCase):
    def test_spaced_legal_form_is_normalised(self):
        from ftm_analyze_de.extract.register import _clean_name

        self.assertEqual(_clean_name("Musterkollektiv e. V."), "Musterkollektiv e.V.")

    def test_bare_legal_form_is_rejected(self):
        from ftm_analyze_de.extract.register import _clean_name

        self.assertIsNone(_clean_name("GmbH"))
        self.assertIsNone(_clean_name(" e. V. "))

    def test_fallback_skips_bare_legal_form(self):
        text = "Nummer der Firma:\nHRB 1\n\nGmbH\n\nBeispiel Handels GmbH\n"
        self.assertEqual(parse_register(text).name, "Beispiel Handels GmbH")


class WrappedNameTest(unittest.TestCase):
    def test_legal_form_on_own_line_is_joined_with_name_above(self):
        text = (
            "Handelsregister B    Nummer der Firma:          HRB 99\n"
            "\n"
            " Nummer   a) Firma                      Grund\n"
            "    1       a)                          \n"
            "\n"
            "            Solarpark Beispieldorf Betrieb       Vertretung\n"
            "\n"
            "        GmbH                                     allein\n"
        )
        self.assertEqual(parse_register(text).name, "Solarpark Beispieldorf Betrieb GmbH")


class CleanupTest(unittest.TestCase):
    def test_role_whitelist(self):
        from ftm_analyze_de.extract.register import _clean_role

        self.assertEqual(_clean_role("Einzelvertretungsberechtigter Vorstand"), "Vorstand")
        self.assertIsNone(_clean_role("Ausgeschieden"))
        self.assertIsNone(_clean_role("Geschäftsanschrift"))

    def test_address_needs_postal_code(self):
        from ftm_analyze_de.extract.register import _find_address

        self.assertEqual(
            _find_address("Geschäftsanschrift: Musterweg 12, 01234 Beispielstadt   Rest"),
            "Musterweg 12, 01234 Beispielstadt",
        )
        self.assertIsNone(_find_address("Geschäftsanschrift:   Geschäftsführer gemeinsam mit einem"))

    def test_seat_after_lone_b(self):
        from ftm_analyze_de.extract.register import _find_seat

        self.assertEqual(_find_seat("   1  a)\n\n   Foo GmbH\n\n   b)\n\n   Beispielstadt\n"), "Beispielstadt")
