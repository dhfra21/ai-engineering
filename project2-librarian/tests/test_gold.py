from eval.gold import article_numbers, is_gold

ITEM = {"gold_doc": "law-2020-5", "gold_articles": [4],
        "evidence": "Art. 4 - Les conditions d'application sont fixées par décret gouvernemental sur proposition du ministre."}


def chunk(doc, article, text):
    return {"doc_id": doc, "article": article, "text": text}


def test_article_numbers_variants():
    assert article_numbers("Art. 3 + Art. 4") == {3, 4}
    assert article_numbers("Article premier") == {1}
    assert article_numbers("الفصل الأول") == {1}
    assert article_numbers("") == set()


def test_gold_by_label_across_languages():
    assert is_gold(chunk("law-2020-5", "الفصل 4", "…"), ITEM)


def test_wrong_law_or_article_is_not_gold():
    assert not is_gold(chunk("law-2020-6", "Art. 4", "…"), ITEM)
    assert not is_gold(chunk("law-2020-5", "Art. 5", "texte sans rapport"), ITEM)


def test_gold_by_evidence_text_when_chunk_has_no_label():
    c = chunk("law-2020-5", "", "x " + ITEM["evidence"] + " y")
    assert is_gold(c, ITEM)
