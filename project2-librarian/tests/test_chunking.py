from src.chunking import chunk_doc, law_ref

AR = """قانون عدد 5 لسنة 2020
باسم الشعب
الفصل الأول ـ يمنع التدخين في الأماكن العمومية.
الفصل 2ـ تضبط الشروط بأمر حكومي.
"""
FR = """Loi n° 2020-5 du 1er janvier 2020.
Article premier - Il est interdit de fumer dans les lieux publics.
Art. 2 - Les conditions sont fixées par décret.
"""


def test_law_ref_both_languages():
    assert law_ref("law-2020-5", "ar") == "قانون عدد 5 لسنة 2020"
    assert law_ref("law-2020-5", "fr") == "Loi n° 2020-5"


def test_article_chunks_carry_label_and_header():
    cs = chunk_doc("law-2020-5", AR, "ar", min_chars=0)
    labels = [c.article for c in cs]
    assert "الفصل الأول" in labels and "الفصل 2" in labels
    assert all(c.text.startswith("قانون عدد 5 لسنة 2020") for c in cs)
    assert all(c.doc_id == "law-2020-5" and c.lang == "ar" for c in cs)


def test_french_articles_split():
    cs = chunk_doc("law-2020-5", FR, "fr", min_chars=0)
    assert [c.article for c in cs if c.article] == ["Article premier", "Art. 2"]


def test_tiny_articles_are_merged():
    cs = chunk_doc("law-2020-5", FR, "fr", min_chars=500)
    assert len([c for c in cs if c.article]) == 1  # both short articles end up in one chunk


def test_long_article_is_split_with_overlap():
    body = "Art. 1 - " + " ".join(f"Phrase numéro {i}." for i in range(400))
    cs = chunk_doc("law-2020-5", body, "fr", max_chars=500, overlap=100)
    assert len(cs) > 3 and all(len(c.text) < 700 for c in cs)
    assert cs[1].text.split("\n", 1)[1][:60] in cs[0].text  # consecutive chunks overlap


def test_fixed_strategy_ignores_articles():
    cs = chunk_doc("law-2020-5", FR, "fr", strategy="fixed")
    assert all(c.article == "" for c in cs)


def test_text_without_articles_falls_back_to_windows():
    cs = chunk_doc("law-2020-5", "Texte sans articles. " * 200, "fr", max_chars=300)
    assert len(cs) > 1
