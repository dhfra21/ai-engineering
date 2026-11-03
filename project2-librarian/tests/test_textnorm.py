from src.textnorm import tokenize


def test_arabic_variants_match():
    # alef variants, ta marbuta, diacritics and the definite article collapse together
    assert tokenize("المحكمةُ") == tokenize("محكمه")
    assert tokenize("أمر") == tokenize("امر")


def test_french_accents_and_stopwords():
    assert tokenize("Le Délai de l'Instance") == ["delai", "instance"]


def test_numbers_are_kept():
    assert "2024" in tokenize("loi n° 2024-41")


def test_mixed_text():
    t = tokenize("قانون عدد 41 Loi 2024")
    assert "41" in t and "loi" in t
