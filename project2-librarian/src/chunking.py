"""Split laws into chunks.

Two strategies, so chunking is a tested decision and not a default:
  article  one chunk per legal article (الفصل / Article); long articles are
           split on sentence boundaries with overlap, short ones are merged
  fixed    sliding window over the whole text

Every chunk carries a header "<law reference> — <article>" so that a chunk
can be understood and cited on its own.
"""
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path

CORPUS = Path(__file__).resolve().parents[1] / "data" / "corpus"

AR_ARTICLE = re.compile(r"^[ \t]*(الفصل[ \t]*(?:[):][ \t]*)?(?:\d+|[^\s\d]+)(?:[ \t]*(?:مكرر|ثالثا|رابعا|خامسا|سادسا|سابعا|ثامنا|تاسعا|عاشرا)\w*)?)", re.M)
FR_ARTICLE = re.compile(
    r"^[ \t]*((?:Article|Art\.)[ \t]*(?:premier|unique|\d+)(?:[ \t]+(?:bis|ter|quater|quinquies|sexies|septies|octies|nonies|decies|\(?nouveau\)?))?)", re.M)


@dataclass
class Chunk:
    id: str
    doc_id: str
    lang: str
    year: int
    number: int
    ref: str       # "قانون عدد 41 لسنة 2024" / "Loi n° 2024-41"
    article: str   # "الفصل 410" / "Article 410", "" if none
    text: str      # header + body: what gets indexed and shown to the LLM


def law_ref(doc_id, lang):
    kind, year, number = doc_id.split("-", 2)
    if lang == "ar":
        word = {"law": "قانون", "decree": "أمر", "decree-law": "مرسوم"}[kind]
        return f"{word} عدد {number} لسنة {year}"
    word = {"law": "Loi", "decree": "Décret", "decree-law": "Décret-loi"}[kind]
    return f"{word} n° {year}-{number}"


def _split_long(body, max_chars, overlap):
    """Split on sentence/line boundaries into windows of <= max_chars with overlap."""
    if len(body) <= max_chars:
        return [body]
    parts, start = [], 0
    while start < len(body):
        end = min(start + max_chars, len(body))
        if end < len(body):
            cut = max(body.rfind("\n", start, end), body.rfind(". ", start, end), body.rfind("؛", start, end))
            if cut > start + max_chars // 2:
                end = cut + 1
        parts.append(body[start:end].strip())
        if end >= len(body):
            break
        start = max(end - overlap, start + 1)
    return [p for p in parts if p]


def _by_article(text, lang, max_chars, overlap, min_chars):
    pat = AR_ARTICLE if lang == "ar" else FR_ARTICLE
    marks = list(pat.finditer(text))
    if not marks:
        return None
    pieces = []
    lead = text[: marks[0].start()].strip()
    if lead:
        pieces.append(("", lead))
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        label = re.sub(r"\s+", " ", m.group(1)).strip()
        pieces.append((label, text[m.start():end].strip()))
    out, i = [], 0
    while i < len(pieces):
        label, body = pieces[i]
        # merge tiny articles into the following ones, up to the size limit
        while len(body) < min_chars and i + 1 < len(pieces) and len(body) + len(pieces[i + 1][1]) <= max_chars:
            i += 1
            body += "\n" + pieces[i][1]
            label = label + (" + " + pieces[i][0] if pieces[i][0] else "")
        for part in _split_long(body, max_chars, overlap):
            out.append((label, part))
        i += 1
    return out


def _fixed(text, max_chars, overlap):
    return [("", p) for p in _split_long(text, max_chars, overlap)]


def chunk_doc(doc_id, text, lang, strategy="article", max_chars=1200, overlap=150, min_chars=200):
    year, number = int(doc_id.split("-")[1]), int(doc_id.split("-")[2])
    ref = law_ref(doc_id, lang)
    pieces = None
    if strategy == "article":
        pieces = _by_article(text, lang, max_chars, overlap, min_chars)
    if pieces is None:  # no article markers, or fixed strategy
        pieces = _fixed(text, max_chars, overlap)
    chunks = []
    for n, (label, body) in enumerate(pieces):
        head = f"{ref} — {label}" if label else ref
        chunks.append(Chunk(f"{doc_id}:{lang}:{n}", doc_id, lang, year, number, ref, label, f"{head}\n{body}"))
    return chunks


def load_chunks(strategy="article", langs=("ar", "fr"), **kw):
    chunks = []
    for lang, folder in (("ar", "txt"), ("fr", "fr")):
        if lang not in langs:
            continue
        for f in sorted((CORPUS / folder).glob("*.txt")):
            chunks += chunk_doc(f.stem, f.read_text(encoding="utf-8"), lang, strategy, **kw)
    return chunks


if __name__ == "__main__":
    import statistics
    for strat in ("article", "fixed"):
        cs = load_chunks(strat)
        lens = [len(c.text) for c in cs]
        by = {l: sum(c.lang == l for c in cs) for l in ("ar", "fr")}
        print(strat, len(cs), by, "median", statistics.median(lens), "p95", sorted(lens)[int(len(lens) * .95)])
    print(json.dumps(asdict(load_chunks("article")[5]), ensure_ascii=False, indent=1)[:800])
