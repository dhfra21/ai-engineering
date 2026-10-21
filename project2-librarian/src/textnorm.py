"""Tokenisation for BM25: normalise Arabic and French so spelling variants match."""
import re
import unicodedata

_DIACRITICS = re.compile("[ً-ٰٟـ]")  # harakat, dagger alef, tatweel
_TOKEN = re.compile(r"[\w]+", re.U)
_FR_STOP = set("le la les l un une des de du d et ou en au aux a à dans par pour sur que qui ce se sa son ses est sont été être il elle ils elles ne pas plus ou où comme sans sous entre ainsi cette ces".split())
_AR_STOP = set("في من على إلى الى عن مع هذا هذه ذلك التي الذي الذين أو او ما لا إن ان أن كل قد تم يتم وفق حسب".split())
_AR_PREFIXES = ("وال", "بال", "كال", "فال", "لل", "ال")


def normalize_ar(s):
    s = _DIACRITICS.sub("", s)
    s = re.sub("[إأآٱ]", "ا", s)
    s = s.replace("ى", "ي").replace("ة", "ه")
    return s


def _stem_ar(tok):
    for p in _AR_PREFIXES:
        if tok.startswith(p) and len(tok) - len(p) >= 3:
            return tok[len(p):]
    return tok


def _strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def tokenize(text):
    text = unicodedata.normalize("NFKC", text).lower()
    out = []
    for tok in _TOKEN.findall(text):
        if re.match(r"[؀-ۿ]", tok):
            tok = _stem_ar(normalize_ar(tok))
            if tok not in _AR_STOP and len(tok) > 1:
                out.append(tok)
        else:
            tok = _strip_accents(tok)
            if tok not in _FR_STOP and (len(tok) > 1 or tok.isdigit()):
                out.append(tok)
    return out
