# Project 2: The Librarian

CS496 AI Engineering, Fall 2026 · 4 Nov 2026 · **Live: http://158.158.120.189**

Ask a question about Tunisian law in Arabic or French. The Librarian finds the right article and answers from it,
citing the law and article for every claim. If the laws don't contain the answer, it says "I don't know".

| | result |
|---|---|
| Right article in the top 5 | 100% (main questions), 76% (paraphrased questions) |
| Answers correct / faithful to their sources | 94% / 95% (after Week 8) |
| Unanswerable questions refused | 22 of 24 |
| Week 8 | p95 latency −52%, for −2 points of correctness |
| Cost per question | $0.0002 |

## 1. The corpus and its users

- **Corpus:** laws from the *Journal Officiel* (iort.gov.tn), 2013–2026: **171 in Arabic, 179 in French**, about
  12 million characters. Public, no personal data, approved by the instructor.
- **Left out:** loan and treaty ratifications (little content), and laws before 2013 (their PDFs extract as junk).
- **Users:** law students, lawyers, journalists and citizens looking for a rule, a deadline or a penalty.
- **Test questions:** 124 (`data/eval/qa.jsonl`): 50 facts asked in both languages, plus 24 questions the laws
  cannot answer. Each has a reference answer and its source article. A second set of **50 paraphrased questions**
  uses everyday wording, with no law numbers: the harder, more honest test.

## 2. How it works

```
question → keyword search + meaning search → merge → reranker picks the best 5 articles → GPT answers with citations
```

| step | choice | why |
|---|---|---|
| Chunks | one per legal article (15,831) | a citation must name a law and an article |
| Index | flat files, exact search | 16k chunks search in milliseconds; a vector database adds nothing at this size |
| Keyword search | BM25, Arabic and French normalised | questions often quote numbers and names |
| Meaning search | OpenAI embeddings (built in 3 min, $0.14) | finds the article even in the other language |
| Reranker | cross-encoder reads the top candidates | biggest accuracy gain, and the slowest step |
| Answer | `gpt-4o-mini`, only from the 5 articles, `[n]` after each claim | faithfulness over fluency |

Details and the reasons behind each choice: `design.md`.

## 3. Retrieval results

Share of questions where the right article is found (main set / paraphrased set):

| search | in top 1 | in top 5 |
|---|---|---|
| keywords only | 87% / 12% | 93% / 32% |
| meaning only | 73% / 34% | 92% / 66% |
| both combined | 84% / 26% | 94% / 58% |
| **both + reranker** | **97% / 52%** | **100% / 76%** |

- **The reranker is the biggest gain:** it puts the right article first in 97% of cases.
- **Keyword search collapses on paraphrased questions** (32%), because users don't use the laws' words. Meaning
  search carries the system there.
- **Cutting by article beats fixed-size chunks** at the top ranks (97% vs 94% in top 1), and makes citations exact.

## 4. Answer quality

124 questions, graded by a second model (`gpt-4.1-mini`) against the reference answers.

| | first version | after prompt fix |
|---|---|---|
| Correct | 87% | **96%** |
| Faithful to the cited articles | not re-measured* | 96% |
| Right article cited | 99% | 99% |
| Unanswerable questions refused | 22 of 24 | 22 of 24 |
| Answerable questions wrongly refused | 0 | 0 |

\* Our grader first checked answers against the wrong sources, which made faithfulness look like 85%. Once fixed, it
was re-run on the improved version only.

- **Most errors were incomplete, not false.** The answer gave the fine but forgot it doubles for repeat offenders.
  Telling the model to include every condition, penalty and exception fixed most of them.
- **Some French questions were answered in Arabic.** A stricter language rule fixed it.
- **A "refuse when the search score is low" rule was dropped.** It looked perfect on the main set but would refuse
  74% of the paraphrased questions.
- **Still failing:** 4–5 answers per 100, mostly budget figures given without their breakdown, and one petrol-price
  question answered from a fuel-tax table.

## 5. Week 8: faster, same accuracy

**Goal:** cut p95 latency or cost by 50%, losing at most 2 points of correctness.

The reranker took almost all the time, so it was the target. Each change was tested on the same 124 questions:

| change | p95 latency | cost | correct | kept? |
|---|---|---|---|---|
| before (reranker reads 30 candidates) | — | $0.00023 | 96% | |
| **reranker reads 10 candidates** | **−52%** | same | **94% (−2)** | **yes** |
| reranker reads shorter text | −31% | same | 93% (−3) | no |
| 15 candidates + shorter text | −43% | −13% | 95% (−1) | no: short of 50% |
| send 3 articles to GPT instead of 5 | −7% | −28% | 92% (−4) | no: answers less complete |
| cheaper model (`gpt-5-nano`) | — | same | empty answers | no |

- **Result:** the latency target is met (−52%), and the accuracy limit is met exactly (−2). A clean re-run measured
  a loss of only 1 point. The cost target was not met: answers already cost $0.0002.
- **Caveat:** the laptop's speed changed during the runs, so the percentages are reliable but the seconds are not.
  Full table and method: `optimisation.md`.

## 6. Known failures and cost

**Known failures:**

- **Old laws and codes are missing.** Only laws from 2013 onward; no Penal Code, no Code of Obligations. Questions
  on drug penalties or contracts get "I don't know".
- **Amendments are not merged.** Each law is stored as published, so the system can cite an article that was later changed.
- **Tables.** Budget laws extract as loose numbers, so figures can come out without their breakdown.
- **Arabic and French versions sometimes differ** in article numbers, and some source files are mislabelled by
  the website.
- **Paraphrased questions:** the right article is in the top 5 only 76% of the time.

**Cost** (`results/cost_model.md`):

| | cost |
|---|---|
| Build the index, once | $0.14 |
| One question | $0.0002 |
| 100 questions a day (class demo) | about $0.60 a month + the VM |
| 10,000 questions a day (100×) | about $60 a month in model fees; hosting grows with the reranker's CPU time, which Week 8 cut by half |

**Not done:** feedback from real users. The site logs 👍/👎, but no user round was run. All numbers come from our
own 174 questions. What went wrong along the way: `postmortem.md`.
