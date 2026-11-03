from eval.threshold_check import table


def test_table_counts_scores_below_each_threshold():
    t = table({"answerable (bad)": [5.0, 3.0, 1.0, -1.0], "unanswerable (good)": [0.5, 4.0]})
    rows = {line.split("|")[1].strip(): line for line in t.splitlines()[2:]}
    assert "25% (1/4)" in rows["0"]            # only -1.0 is below 0
    assert "50% (2/4)" in rows["2"] and "50% (1/2)" in rows["2"]   # 1.0 and -1.0 below 2; only 0.5 below 2
    assert "75% (3/4)" in rows["4"] and "50% (1/2)" in rows["4"]   # 3, 1, -1 are below 4; only 0.5 is (4.0 is not)
