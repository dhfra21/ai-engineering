# Postmortem

What went wrong in Project 2, what it cost, and what we would do differently. Written 3 Nov 2026; the
section on generation failures is empty until the baseline run is in.

## 1. The corpus took longer than the code

We started with the handbook idea in the scaffold, then chose Tunisian laws. The first sources did not work:
the Constitution PDF we had extracts as scrambled characters (a print driver with a custom font), the official
URL carried an expired session token, and the "download PDF" button for each legal code returns only a cover page
(the full codes are sold). Only individual laws in the search have real text, and only from 2013 on: older PDFs
use legacy fonts and extract as junk. Finding that took a long exploration of the site, and the final corpus is
171 Arabic and 179 French laws, mostly finance and institutional laws, not the codes we first had in mind.
**Lesson:** test text extraction on three real files before choosing a corpus, not after.

## 2. The scraper broke in five different ways

The site is a stateful application where every click needs the session of the previous one.

- **Wrong numbers.** The first version read "law n, year y" from anywhere in a title, so a law that mentions
  another law got that law's number (it fetched "law 3 of 1972"). Fixed by anchoring on the start of the title.
- **Expired sessions.** One long listing run silently returned 0 laws for 2017-2026. Fixed by re-listing in a new
  session; the fetcher now retries with a fresh session and a pause.
- **A page that cannot go back.** The French text lives on a detail page that cannot return to the result list, so
  every row returned the same law until we opened a fresh session per text (about 6 s each).
- **The site serves the wrong file.** For some rows the PDF is another law (41 cases, logged), and some Arabic
  files contain the end of the previous law. We now name each document by the number found in its own text. This
  was only found because a spot check showed a law-47 file starting with "law 46".
- **A case-sensitive parser.** A unit test found that the French extractor looked for `</STYLE>` and silently
  returned nothing on lowercase markup.

## 3. Index builds were slow, blind and duplicated

Embedding 15,831 chunks with the local e5 model took **57 minutes** on 8 CPU cores, then **44 minutes** more for the
fixed-window ablation. The first build printed no progress, so we waited without knowing whether it was 10% or 90%
done. Hour-long builds were also repeated across machines before there was a way to share an index. Fixes: progress
logging, `meta.json` with a hash of the chunks so embeddings can be reused (`scripts/pack_index.sh`), and the
OpenAI embedding backend, which builds the same index in **166 s for $0.135**.
**Lesson:** time a 100-chunk sample before an hour-long job, and make expensive artefacts shareable from the start.

## 4. We switched embedding models mid-project

Moving from local e5 to OpenAI embeddings meant re-running every retrieval evaluation (about 40 minutes of
reranker time per set) and keeping both indexes side by side so the baseline numbers stay valid. The result was
not clear-cut: overall about equal, better in French, worse in Arabic on only 25 facts per language. We chose
OpenAI for build time and deployment size, not for quality, and the report says so.

## 5. Our first evaluation set was too easy

The 100 answerable questions were written from the articles and reuse their words, so keyword search alone reached
**93% recall@5**, the reranker 100%, and the ablation looked like "everything works". Only after writing 50
paraphrased questions did the picture change: keyword search drops to 32%, hybrid becomes **worse than vector-only**
(58% vs 66%), and even the reranker stops at 76%. The headline number would have been misleading without it.
**Lesson:** write the hard questions first; a good score on an easy set is not a result.

## 6. Gold labels are not trivial for amending laws

Writing the question set, we found that article numbers in the Arabic and French versions of an *amending* law
differ, and that some Arabic files contain a neighbour law. We kept only pairs verified in both languages. It still
bit us once in testing: asking for the delay in which election results are announced returned the 2024 amending
law (Court of Cassation, presidential elections) while the gold label was the 2014 law. The answer was faithful to its
source, so the label, not the system, was out of date. This is the general problem of a corpus without consolidated
law: the system cannot tell which version is in force.

## 7. Latency numbers depend on what else is running

The reranker took 7.4 s per query in the first run and 9.1 s in a later run on the same machine, during which we were also working on it (likely, not proven, the cause). Before/after
numbers for Week 8 are only comparable if measured on one idle machine, so DF keeps all latency runs on their
machine and nothing else runs during them.

## 8. Smaller problems

- The course key does not list `gpt-4o`, so the default judge failed until we switched it to `gpt-4.1-mini`.
- **The API key was pasted into a chat session** to share it. It is stored only in a git-ignored `.env`, but treat
  it as exposed: set a spending limit on it before the URL is shared, and do not paste keys again; share them
  through a private channel.
- On Windows, several `open()` calls used the default cp1252 encoding and failed on Arabic text (fix: run with
  `PYTHONUTF8=1`; the proper fix is `encoding="utf-8"` everywhere).
- A French question was abstained from in Arabic (the "I don't know" phrase was fixed). Found by testing in both languages.
- The container build of the service is untested because the development machine has no Docker.

## 9. Generation failures **[TO FILL after the baseline run]**

To be completed from `results/generation_baseline.json`: the questions the judge marked wrong, whether they
are retrieval misses, prompt problems or judge errors, how many unanswerable questions were answered anyway, how
many answerable ones were refused, and whether the failures are concentrated in Arabic or French.

## 10. What we would do differently

1. Check text extraction before choosing the corpus, and scrape one year first.
2. Write the paraphrased questions before building anything, and report both sets from the start.
3. Add progress logging and a size/time estimate to every long job, and share artefacts through a release from day one.
4. Merge the Arabic and French versions of each law into one record (with the law number as key) so a question in one
   language can use the other.
5. Keep latency measurements on a single idle machine and write down what else is running.
