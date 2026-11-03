from src.ingest.iort_scrape import SKIP_TITLE, french_text, is_arabic, parse_rows, parse_title


def test_parse_title_leading_number_only():
    t = parse_title("قانون أساسي عدد 38 لسنة 2024 مؤرخ في 19 جويلية 2024 يتعلق بالموافقة")
    assert (t["number"], t["year"]) == (38, 2024)
    # a number inside the title refers to another text and must not be taken
    assert parse_title("يتعلق بالمصادقة على المرسوم عدد 1 لسنة 1990")["number"] is None


def test_loan_ratifications_are_skipped():
    assert SKIP_TITLE.search("قانون عدد 43 لسنة 2024 يتعلق بالموافقة على اتفاق القرض المبرم")
    assert not SKIP_TITLE.search("قانون عدد 41 لسنة 2024 يتعلق بتنقيح بعض أحكام المجلة التجارية")


def test_is_arabic_rejects_junk_and_short():
    assert is_arabic("الفصل الأول ـ يمنع التدخين في الأماكن العمومية. " * 20)
    assert not is_arabic("s‡‡O½«u‡I« Ê«u¹b?Ð " * 80)
    assert not is_arabic("قصير")


def test_parse_rows_reads_title_and_row_index():
    html = ("<a name=A17 href=\"javascript:_PAGE_.A4.value=3;javascript:{_JSL(_PAGE_,'A17','_blank','','')}\" "
            "CLASS=x>قانون عدد 5 لسنة 2020 مؤرخ في 1 جانفي 2020</a>")
    assert parse_rows(html) == [(3, "قانون عدد 5 لسنة 2020 مؤرخ في 1 جانفي 2020")]


def test_french_text_stops_before_arabic_version():
    html = ("<html><style></style><body>menu <br>Loi n° 2016-75 du 8 décembre 2016, portant approbation de x. "
            "Article unique - Est approuvé l'accord annexé à la présente loi. "
            "Tunis, le 8 décembre 2016. Le Président de la République. " + "Texte français. " * 20 +
            "<br>قانون عدد 75 لسنة 2016 مؤرخ في 8 ديسمبر 2016</body></html>")
    fr, ident = french_text(html)
    assert ident == (2016, 75)
    assert "Article unique" in fr and "قانون" not in fr
