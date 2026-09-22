"""Agreement and summary statistics. Pure stdlib, unit-tested in tests/.

The brief asks for counts AND percentages, never one summary number — so
helpers here return both, and `frac()` formats them as "12/40 (30.0%)".
"""
from __future__ import annotations

import math
from collections import Counter
from typing import Hashable, Sequence


def frac(n: int, d: int) -> str:
    return f"{n}/{d} ({100 * n / d:.1f}%)" if d else f"{n}/0 (n/a)"


def wilson_interval(n: int, d: int, z: float = 1.96) -> tuple[float, float]:
    """95% confidence interval for a proportion n/d. Better than the normal
    approximation at the small sample sizes we have (tens of items)."""
    if d == 0:
        return (float("nan"), float("nan"))
    p = n / d
    denom = 1 + z * z / d
    centre = (p + z * z / (2 * d)) / denom
    half = z * math.sqrt(p * (1 - p) / d + z * z / (4 * d * d)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def proportion(n: int, d: int) -> dict:
    lo, hi = wilson_interval(n, d)
    return {"n": n, "of": d, "pct": round(100 * n / d, 1) if d else None,
            "ci95_pct": [round(100 * lo, 1), round(100 * hi, 1)] if d else None}


def cohen_kappa(a: Sequence[Hashable], b: Sequence[Hashable]) -> float | None:
    """Chance-corrected agreement between two raters over the same items.
    1 = perfect, 0 = no better than chance given each rater's label rates.
    Returns None when undefined (fewer than 1 item, or both raters constant
    on the same single label)."""
    if len(a) != len(b):
        raise ValueError("raters must label the same items")
    n = len(a)
    if n == 0:
        return None
    observed = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    expected = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    if expected == 1:
        return None
    return (observed - expected) / (1 - expected)


def confusion(a: Sequence[Hashable], b: Sequence[Hashable], labels: Sequence[Hashable]) -> dict:
    """counts[row_label][col_label] with rows = a, columns = b."""
    table = {r: {c: 0 for c in labels} for r in labels}
    for x, y in zip(a, b):
        table[x][y] += 1
    return table


def agreement_report(a: Sequence[str], b: Sequence[str], labels=("good", "bad"),
                     positive: str = "bad") -> dict:
    """Everything we report when comparing two label sequences (human vs human,
    or human vs judge). `positive` is the class we care about catching — for a
    judge, missing a bad answer is the expensive mistake."""
    n = len(a)
    agree = sum(x == y for x, y in zip(a, b))
    k = cohen_kappa(a, b)
    tp = sum(x == positive and y == positive for x, y in zip(a, b))
    a_pos = sum(x == positive for x in a)
    b_pos = sum(y == positive for y in b)
    return {
        "n": n,
        "agreement": proportion(agree, n),
        "cohen_kappa": round(k, 3) if k is not None else None,
        "confusion_rows_a_cols_b": confusion(a, b, labels),
        f"a_{positive}_rate": proportion(a_pos, n),
        f"b_{positive}_rate": proportion(b_pos, n),
        # Treating `a` as ground truth: of the items a calls positive, how many b also catches…
        f"recall_of_{positive}": proportion(tp, a_pos),
        # …and of the items b calls positive, how many a agrees with.
        f"precision_of_{positive}": proportion(tp, b_pos),
    }


def kappa_words(k: float | None) -> str:
    """Landis & Koch (1977) bands — conventional, if arbitrary."""
    if k is None:
        return "undefined"
    for bound, word in [(0, "poor"), (0.2, "slight"), (0.4, "fair"), (0.6, "moderate"),
                        (0.8, "substantial"), (1.01, "almost perfect")]:
        if k < bound:
            return word
    return "almost perfect"


def percentile(values: Sequence[float], p: float) -> float | None:
    xs = sorted(v for v in values if v is not None)
    if not xs:
        return None
    k = (len(xs) - 1) * p / 100
    lo, hi = math.floor(k), math.ceil(k)
    return round(xs[lo] + (xs[hi] - xs[lo]) * (k - lo), 1)
