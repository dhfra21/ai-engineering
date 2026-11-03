# Postmortem

What went wrong in Project 2, what it cost, and what we would do differently. Written 3 Nov 2026, with the generation
results of the baseline and of the tuned run.

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

## 9. Generation failures

From the baseline (`results/generation_baseline.json`) and the tuned run re-judged after fixing the judge
(`results/generation_tuned_judgefix.json`).

- **The metric was wrong before the system was.** Faithfulness read 83-85%, which looked like a real problem,
  and many "unsupported claims" were the whole answer copied word for word from its source. The cause was in our
  judge: it showed the cited sources as `[1]..[k]` while the answer cites their original positions
  (`[3][4]`). After the fix faithfulness is **96%**. We would have spent the optimisation time on a defect that
  did not exist. We found it only by reading the flagged rows.
- **Wrong answers were mostly incomplete answers.** 11 of the 13 baseline errors dropped one fact the reference
  had (a doubled fine, a breakdown of figures, where identities are recorded). Asking the model for complete
  answers took correctness from 87% to 95-96%, with one new side effect: an answer that adds conditions from
  another law (1 case) and lower citation precision (96% to 91%).
- **Answers in the wrong language.** Three French questions were answered in Arabic, including 9 of 12 French
  refusals ("لا أعرف" to a French question). A prompt rule fixed most of it; one Arabic question was still
  refused in French, so the refusal phrase is now chosen in code from the question's language.
- **One answer built on the wrong chunk.** For a French question on how senior posts are filled, the gold
  article was among the 5 retrieved chunks but the answer used another one ("by government decree" instead of
  "by order of the head of government"). Retrieval was right; generation picked the wrong source. It is the only
  answer both wrong and unfaithful.
- **A question the corpus cannot answer was answered.** The petrol price came back as fuel duties from a
  finance law (5 millimes per litre, 41.382 dinars per hectolitre) presented as the price; the refusal threshold (2.0) fixed it. The minimum-wage question was answered
  with "the amount is not specified in the sources" while citing a pension law: a refusal in substance that our
  strict metric counts as an answer. The threshold was tuned on the same questions it is scored on, so the 23 of 24 is
  optimistic until it is checked on the paraphrased set.
- **No over-refusal on this set** (0 of 100 answerable questions refused), but that set reuses the laws' own
  wording; whether 2.0 refuses real answers on paraphrased questions is not known.

## 10. What we would do differently

1. Check text extraction before choosing the corpus, and scrape one year first.
2. Write the paraphrased questions before building anything, and report both sets from the start.
3. Add progress logging and a size/time estimate to every long job, and share artefacts through a release from day one.
4. Merge the Arabic and French versions of each law into one record (with the law number as key) so a question in one
   language can use the other.
5. Keep latency measurements on a single idle machine and write down what else is running.
6. When a metric looks bad, read the failing rows before changing the system: our worst number was a bug in the judge.
