# Cost model (from DF's generation baseline: 124 questions, article-oai, hybrid+rerank, k=5)

Measured on 124 requests; generator `gpt-4o-mini`. Abstained: 18%.

| Item | Value |
|---|---|
| Generation per request | $0.00021 |
| Question embedding per request (25 tokens) | $0.0000005 |
| **Total per request** | **$0.00021** |
| Latency p50 / p95 | 4.9 s / 5.8 s |
| Index build, once | $0.135 |

| Scenario | Requests per day | Model fees per month | Workers needed | Hosting per month |
|---|---|---|---|---|
| today | 100 | $0.63 | 1 | $0 (free CPU Space) |
| 100x | 10,000 | $62.57 | 3 | $90 |

**Assumptions** (change them with the options of `eval/cost_model.py`):
- today = 100 requests per day (a class using it for a demo); 100x = 10,000.
- one worker handles one request at a time for its whole latency (the reranker is CPU-bound), run at 25% utilisation to leave headroom for peaks.
- a worker costs $30 per month (an assumed price for a small CPU VM, not a quote).
- prices come from `src/config.py` (list prices); judge calls are an evaluation cost, not a serving cost.
- hosting grows with the reranker's CPU time (5-9 s per request depending on the machine), while model fees are cents per thousand requests: that is why the reranker is the Week 8 target.
