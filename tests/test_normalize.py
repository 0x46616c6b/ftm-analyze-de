from ftm_analyze_de.normalize import dedupe, fold, repair_hyphenation


def test_repair_hyphenation():
    assert repair_hyphenation("Geschäfts-\nführer und Sachsen-\nAnhalt") == "Geschäftsführer und Sachsen-\nAnhalt"


def test_fold():
    assert fold("Müller  Straße") == fold("Mueller strasse")


def test_dedupe_prefers_umlauts():
    assert dedupe({"Hans Müller", "Hans Mueller", "Erika Muster"}) == {"Hans Müller", "Erika Muster"}
