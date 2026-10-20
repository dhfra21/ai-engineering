"""Scrape Tunisian laws from the IORT (Imprimerie Officielle) public search.

The site is a stateful WinDev app: every session has its own /CTX_xxx/ path,
pages are navigated by POSTing WD_BUTTON_CLICK_=<action>, and result rows are
selected by a row index (A4) relative to the current page of 15.

Usage:
  python -m src.ingest.iort_scrape list  --years 2000-2024 --types law
  python -m src.ingest.iort_scrape fetch --years 2000-2024 --types law

`list` writes data/corpus/manifest.jsonl (metadata only); `fetch` downloads the
PDFs of every manifest row that passes the filter, extracts the text with
pdftotext and writes data/corpus/txt/<id>.txt. Raw PDFs go in
data/corpus/raw/ (git-ignored). Be polite: one request at a time, with a delay.
"""
import argparse
import html
import json
import re
import subprocess
import time
import unicodedata
from pathlib import Path

import httpx

HOST = "http://www.iort.gov.tn"
START = HOST + "/WD120AWP/WD120Awp.exe/CONNECT/SITEIORT"
CORPUS = Path(__file__).resolve().parents[2] / "data" / "corpus"
MANIFEST = CORPUS / "manifest.jsonl"
RAW = CORPUS / "raw"
TXT = CORPUS / "txt"
DELAY = 1.0
PAGE = 15
BIDI = re.compile("[\u200e\u200f\u202a-\u202e\u2066-\u2069]")

# value of the A9 <select> on the search form
TYPES = {"law": 2, "decree-law": 3, "decree": 4, "order": 5}
TYPE_AR = {"law": "قانون", "decree-law": "مرسوم", "decree": "أمر", "order": "قرار"}

# Ratifications of loans/treaties are legally valid but add noise, not content.
SKIP_TITLE = re.compile(
    r"الموافقة على (اتفاق|عقد|الملحق|بروتوكول|ملحق|مذكرة)|المصادقة على|القرض|"
    r"قرض|الانضمام إلى|اتفاقية|معاهدة|اتفاق"
)


class Session:
    def __init__(self):
        self.c = httpx.Client(follow_redirects=True, timeout=90,
                              headers={"User-Agent": "CS496-student-research/1.0"})
        self.action_url = None

    def _sleep(self):
        time.sleep(DELAY)

    def _track(self, r):
        if "text/html" in r.headers.get("content-type", ""):
            m = re.search(r'<FORM [^>]*ACTION="([^"]+)"', r.text, re.I)
            if m:
                self.action_url = HOST + m.group(1)
        return r

    def get(self, url):
        self._sleep()
        return self._track(self.c.get(url))

    def click(self, action, **fields):
        self._sleep()
        data = {"WD_BUTTON_CLICK_": action, "WD_ACTION_": ""}
        data.update({k: str(v) for k, v in fields.items()})
        return self._track(self.c.post(self.action_url, data=data))

    def open_search(self):
        r = self.get(START)
        base = re.search(r'href="(/WD120AWP/[^"?]*/Principal/SYNC_[-\d]+)\?M22"', r.text).group(1)
        self.get(f"{HOST}{base}?M7")
        self.click("A9", A12=-1, A12_DEB=1, _A12_OCC=0)

    def search(self, year, kind):
        # A8 option values: 2 -> 2026, 3 -> 2025, ...
        r = self.click("A40", A5="", A8=2028 - year, A6="", A3="", A9=TYPES[kind],
                       A27=1, A26=1, A14=1, A4=-1, A4_DEB=1, _A4_OCC=0)
        return r.text

    def page(self, offset):
        url = re.sub(r"\?.*", "", self.action_url) + f"?WD_ACTION_=SCROLLTABLE&ZR_RechercheArijMinistere={offset}"
        return self.get(url).text


def parse_rows(page_html):
    rows = []
    for m in re.finditer(r"A4\.value=(\d+);javascript:\{_JSL\(_PAGE_,'A17'[^>]*>(.*?)</a>", page_html, re.S):
        title = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", m.group(2)))).strip()
        rows.append((int(m.group(1)), title))
    return rows


def parse_title(title):
    # only a leading "قانون [أساسي] عدد N لسنة Y": older titles carry no number,
    # and later "عدد N لسنة Y" are references to other texts
    num = re.match(r"\s*(?:قانون|مرسوم)[^\d]{0,30}?عدد\s+(\d+)\s+لسنة\s+(\d{4})", title)
    date = re.search(r"مؤرّ?خ في\s+(.*?)\s+(?:يتعلّ?ق|في |المتعلق|بشأن|$)", title)
    return {
        "number": int(num.group(1)) if num else None,
        "year": int(num.group(2)) if num else None,
        "date_text": date.group(1) if date else None,
    }


def parse_years(s):
    a, _, b = s.partition("-")
    return list(range(int(a), int(b or a) + 1))


def cmd_list(args):
    CORPUS.mkdir(parents=True, exist_ok=True)
    seen = set()
    if MANIFEST.exists():
        seen = {(r["kind"], r["year"], r["number"], r["title"]) for r in map(json.loads, MANIFEST.open())}
    s = Session()
    s.open_search()
    with MANIFEST.open("a") as out:
        for kind in args.types:
            for year in parse_years(args.years):
                first = s.search(year, kind)
                offset, n_year, last_first = 0, 0, None
                body = first
                while True:
                    rows = parse_rows(body)
                    if not rows or rows[0][1] == last_first:
                        break
                    last_first = rows[0][1]
                    for idx, title in rows:
                        meta = parse_title(title)
                        rec = {"kind": kind, "list_year": year, "title": title, "page_offset": offset,
                               "row": idx, **meta}
                        key = (kind, rec["year"], rec["number"], title)
                        if key in seen:
                            continue
                        seen.add(key)
                        out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                        n_year += 1
                    out.flush()
                    offset += PAGE
                    body = s.page(offset)
                print(f"{kind} {year}: {n_year} texts", flush=True)


def doc_id(rec):
    return f"{rec['kind']}-{rec['year']}-{rec['number']}"


def is_arabic(text):
    """Pre-2013 PDFs use legacy fonts and extract as junk; reject those."""
    letters = [c for c in text if c.isalpha()]
    ar = sum("\u0621" <= c <= "\u064a" for c in letters)
    return len(letters) > 300 and ar / len(letters) > 0.8


FR_START = re.compile(r"(Loi organique|Loi|Décret-loi|Décret|Arrêté)\s+n°")
AR_START = re.compile(r"[\u0621-\u064a]{3}")


def french_text(page_html):
    """The two-language page holds the French text, then the Arabic one."""
    body = re.sub(r"<SCRIPT.*?</SCRIPT>", "", page_html[page_html.find("</STYLE>"):], flags=re.S)
    body = re.sub(r"<(br|BR|/p|/P|/TR|/tr|/div)[^>]*>", "\n", body)
    t = html.unescape(re.sub(r"<[^>]+>", " ", body))
    t = re.sub(r"[ \t\u00a0]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n", t)
    m = FR_START.search(t)
    if not m:
        return None, None
    t = t[m.start():]
    # cut at the first line that is Arabic, and drop the site footer
    cut = re.search(r"\n\s*[\u0621-\u064a]", t)
    fr = t[: cut.start()] if cut else t
    head = re.match(r"(?:Loi organique|Loi|Décret-loi|Décret|Arrêté)\s+n°\s*(\d{4})-(\d+)", fr)
    return fr.strip(), (int(head.group(1)), int(head.group(2))) if head else None


def cmd_fetch_fr(args):
    FR = CORPUS / "fr"
    FR.mkdir(parents=True, exist_ok=True)
    recs = [json.loads(l) for l in MANIFEST.open()]
    for r in recs:
        r.update(parse_title(r["title"]))
    todo = [r for r in recs if r["number"] and r["kind"] in args.types
            and r["list_year"] in parse_years(args.years) and not SKIP_TITLE.search(r["title"])]
    todo.sort(key=lambda r: (r["list_year"], r["page_offset"], r["row"]))
    if args.limit:
        todo = todo[: args.limit]
    print(f"{len(todo)} documents to try", flush=True)
    for r in todo:
        did = doc_id(r)
        if (FR / f"{did}.txt").exists():
            continue
        for attempt in (1, 2, 3):
            time.sleep(5 * (attempt - 1))
            # the detail page cannot go back to the results list: use a fresh session per text
            s = Session()
            s.open_search()
            s.search(r["list_year"], r["kind"])
            if r["page_offset"]:
                s.page(r["page_offset"])
            resp = s.click("A16", A4=r["row"], A4_DEB=1, _A4_OCC=PAGE)
            if "AFFICHETEXTEJURIDIQUEINTEGRAL" in resp.text.upper():  # detail page; Arabic-only ones have no French
                break
            continue  # retry with a new session after a pause
        else:
            print("no page:", did, flush=True)
            continue
        fr, ident = french_text(resp.text)
        if not fr or len(fr) < 200:
            print("no french:", did, flush=True)
            continue
        out = f"{r['kind']}-{ident[0]}-{ident[1]}" if ident else did
        (FR / f"{out}.txt").write_text(fr, encoding="utf-8")
        print("ok", out, len(fr), flush=True)


def cmd_fetch(args):
    RAW.mkdir(parents=True, exist_ok=True)
    TXT.mkdir(parents=True, exist_ok=True)
    recs = [json.loads(l) for l in MANIFEST.open()]
    for r in recs:
        r.update(parse_title(r["title"]))
    todo = [r for r in recs if r["number"] and r["kind"] in args.types
            and r["list_year"] in parse_years(args.years)
            and not SKIP_TITLE.search(r["title"]) and not (TXT / f"{doc_id(r)}.txt").exists()]
    todo.sort(key=lambda r: (r["list_year"], r["page_offset"], r["row"]))
    if args.limit:
        todo = todo[: args.limit]
    print(f"{len(todo)} documents to fetch", flush=True)
    s = Session()
    s.open_search()
    cur = None
    for r in todo:
        if cur != (r["kind"], r["list_year"]):
            s.search(r["list_year"], r["kind"])
            cur = (r["kind"], r["list_year"])
            at_offset = 0
        if r["page_offset"] != at_offset:
            s.page(r["page_offset"])
            at_offset = r["page_offset"]
        resp = s.click("A7", A4=r["row"], A4_DEB=1, _A4_OCC=PAGE)
        if "pdf" not in resp.headers.get("content-type", ""):
            # session probably expired: start over and re-navigate to the row
            s = Session()
            s.open_search()
            s.search(r["list_year"], r["kind"])
            if r["page_offset"]:
                s.page(r["page_offset"])
            at_offset = r["page_offset"]
            resp = s.click("A7", A4=r["row"], A4_DEB=1, _A4_OCC=PAGE)
        if "pdf" not in resp.headers.get("content-type", ""):
            print("no pdf:", doc_id(r), flush=True)
            continue
        raw_pdf = resp.content
        tmp = RAW / "_tmp.pdf"
        tmp.write_bytes(raw_pdf)
        text = subprocess.run(["pdftotext", str(tmp), "-"], capture_output=True, text=True).stdout
        # 2013+ PDFs use Arabic presentation forms: NFKC maps them back to plain letters
        text = BIDI.sub("", unicodedata.normalize("NFKC", text))
        if not is_arabic(text):
            print("garbled/short text, skipped:", doc_id(r), flush=True)
            continue
        # The site's PDF links are sometimes wired to the wrong file, so name
        # the document by what it says it is, not by the row we clicked.
        head = re.sub(r"\s+", " ", text[:400])
        m = re.search(r"عدد\s*(\d+)\s*لسنة\s*(\d{4})", head)
        if m:
            got = {**r, "number": int(m.group(1)), "year": int(m.group(2))}
        else:
            got = r
        did = doc_id(got)
        if did != doc_id(r):
            with (CORPUS / "mismatch.log").open("a") as f:
                f.write(f"asked {doc_id(r)} got {did}\n")
        if (TXT / f"{did}.txt").exists():
            print("dup/mismatch", doc_id(r), "->", did, flush=True)
            continue
        tmp.rename(RAW / f"{did}.pdf")
        (TXT / f"{did}.txt").write_text(text, encoding="utf-8")
        with (CORPUS / "docs.jsonl").open("a") as f:
            f.write(json.dumps({"id": did, "kind": got["kind"], "year": got["year"], "number": got["number"],
                                "title": r["title"] if did == doc_id(r) else head[:200], "chars": len(text)},
                               ensure_ascii=False) + "\n")
        print("ok", did, len(text), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["list", "fetch", "fetch-fr"])
    p.add_argument("--years", default="2024")
    p.add_argument("--types", nargs="+", default=["law"], choices=list(TYPES))
    p.add_argument("--limit", type=int, default=0)
    a = p.parse_args()
    {"list": cmd_list, "fetch": cmd_fetch, "fetch-fr": cmd_fetch_fr}[a.cmd](a)
