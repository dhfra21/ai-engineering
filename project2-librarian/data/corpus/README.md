# Corpus: Tunisian laws from the Journal Officiel (2013–2026)

Source texts for Project 2 (The Librarian). Everything here is public legal text
published by the Imprimerie Officielle de la République Tunisienne
([iort.gov.tn](http://www.iort.gov.tn/)). It contains no personal data.

## What is in it

| Folder / file | Content |
|---|---|
| `txt/` | Arabic text of 171 laws, one file per law (`law-<year>-<number>.txt`), 5.5 M characters |
| `fr/` | French text of 179 laws, same naming, 6.5 M characters |
| `manifest.jsonl` | Metadata for the 2,910 laws the site listed for 1990–2026 (title, year, number, position in the site's result list) |
| `docs.jsonl` | One line per Arabic text that was downloaded: id, year, number, title, length |
| `mismatch.log` | Rows where the site served a different law than the one requested (41 cases) |
| `raw/` | The downloaded Arabic PDFs (git-ignored, re-fetchable) |

134 laws exist in both languages, 37 in Arabic only and 45 in French only.
Laws per year (Arabic): 2013: 6, 2014: 9, 2015: 15, 2016: 26, 2017: 19, 2018: 21,
2019: 18, 2020: 11, 2021: 6, 2023: 4, 2024: 21, 2025: 9, 2026: 6 (none in 2022).

Laws are ordinary laws and organic laws (*lois organiques*), covering elections,
the judiciary, banking, public finance, labour, local government and more.
Budget-settlement and finance laws are the largest files (up to about 500 k
characters each) and are mostly tables.

## How it was built

Scraper: [`../../src/ingest/iort_scrape.py`](../../src/ingest/iort_scrape.py).
The site is a stateful web application, so the scraper opens a session,
runs the "search for a text" form by year and type, and clicks through results at
one request per second.

```bash
python -m src.ingest.iort_scrape list     --years 2013-2026 --types law   # -> manifest.jsonl
python -m src.ingest.iort_scrape fetch    --years 2013-2026 --types law   # Arabic PDFs -> txt/
python -m src.ingest.iort_scrape fetch-fr --years 2013-2026 --types law   # French text -> fr/
```

Choices made while building it:

- **Arabic** comes from each law's PDF, extracted with `pdftotext`, normalised
  with Unicode NFKC (the PDFs use Arabic presentation forms) and stripped of
  bidirectional control characters.
- **French** comes from the HTML of the site's two-language page, which holds
  the French text followed by the Arabic one; only the French part is kept.
- **Skipped on purpose:** ratifications of loans, treaties and agreements
  (matched by title keywords such as الموافقة على اتفاق, المصادقة على, القرض).
  They are legally valid but add little content.

## Known problems

- **Only 2013 onward.** Older PDFs are encoded with legacy fonts and extract as
  unreadable characters, and the 1995 text I tried returned a scanned blob instead of a PDF.
  The scraper rejects any text that is less than 80 % Arabic letters;
  7 laws from 2013 were rejected this way.
- **The site mislabels files.** Some PDF links return a different law than the
  one requested, and some Arabic files contain the end of the previous law or the
  start of the next one (a gazette page can span two laws). Each file is named by
  the law number found in its own text, and mismatches are logged. Article
  numbers in the Arabic and French versions of an *amending* law can differ,
  because the Arabic file may include a neighbouring law, so check both
  languages before using an article as a gold label.
- **Coverage is uneven.** 2022 has no laws in the corpus, and the Arabic side is
  thinner than the French one (see the counts above).
- **Layout noise.** Page headers, footnotes ("Travaux préparatoires") and table
  of contents lines are left in the text. Tables in finance laws extract as
  loose lines of numbers.
- **Not legal advice.** The texts are the originals as published; later
  amendments are not merged in. Only the Journal Officiel itself is authoritative.

## Using it

`src/chunking.py` splits each file by article (الفصل / Article) and
`src/index.py` builds the search index from `txt/` and `fr/`. The evaluation
questions in `../eval/qa.jsonl` point at these files by law id and article number.
