# Refusal threshold check

Share of questions refused when the best reranker score is below the threshold.
Wrong refusals (answerable) should be low, right refusals (unanswerable) high.

| threshold | answerable, main set (bad) refused | answerable, paraphrased (bad) refused | unanswerable (good) refused |
|---|---|---|---|
| 0 | 0% (0/100) | 40% (20/50) | 67% (16/24) |
| 1 | 0% (0/100) | 62% (31/50) | 75% (18/24) |
| 1.5 | 0% (0/100) | 70% (35/50) | 83% (20/24) |
| 2 | 0% (0/100) | 74% (37/50) | 88% (21/24) |
| 2.5 | 0% (0/100) | 76% (38/50) | 88% (21/24) |
| 3 | 1% (1/100) | 80% (40/50) | 88% (21/24) |
| 4 | 3% (3/100) | 84% (42/50) | 92% (22/24) |
