import unittest

from harness import stats


class TestStats(unittest.TestCase):
    def test_kappa_perfect_and_chance(self):
        self.assertEqual(stats.cohen_kappa(["good", "bad"] * 5, ["good", "bad"] * 5), 1.0)
        # Rater b is constant: observed 50% agreement is exactly what chance predicts.
        self.assertAlmostEqual(stats.cohen_kappa(["good", "bad"] * 5, ["good"] * 10), 0.0)

    def test_kappa_known_value(self):
        # 20 items: both good 8, both bad 7, a good/b bad 3, a bad/b good 2.
        a = ["good"] * 8 + ["bad"] * 7 + ["good"] * 3 + ["bad"] * 2
        b = ["good"] * 8 + ["bad"] * 7 + ["bad"] * 3 + ["good"] * 2
        # po = 15/20 = .75; pe = (11*10 + 9*10)/400 = .5; kappa = .5
        self.assertAlmostEqual(stats.cohen_kappa(a, b), 0.5)

    def test_kappa_undefined(self):
        self.assertIsNone(stats.cohen_kappa([], []))
        self.assertIsNone(stats.cohen_kappa(["good"] * 3, ["good"] * 3))

    def test_agreement_report(self):
        a = ["bad", "bad", "good", "good"]
        b = ["bad", "good", "good", "bad"]
        r = stats.agreement_report(a, b)
        self.assertEqual(r["agreement"]["n"], 2)
        self.assertEqual(r["recall_of_bad"]["n"], 1)
        self.assertEqual(r["recall_of_bad"]["of"], 2)
        self.assertEqual(r["confusion_rows_a_cols_b"]["good"]["bad"], 1)

    def test_wilson_bounds(self):
        lo, hi = stats.wilson_interval(10, 10)
        self.assertLess(lo, 1.0)
        self.assertEqual(hi, 1.0)

    def test_frac_and_percentile(self):
        self.assertEqual(stats.frac(3, 12), "3/12 (25.0%)")
        self.assertEqual(stats.percentile([1, 2, 3, 4, None], 50), 2.5)


if __name__ == "__main__":
    unittest.main()
