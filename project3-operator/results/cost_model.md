# Cost model (from eval `v2`, 41 tasks)

Measured per task: **3104 input + 414 output tokens**, 3.0 steps on average (p95 5), max 7.
Latency per task, model time only (no rate-limit waits): not recorded in this run.

| model | $ per task | $/month today (300 tasks) | $/month at 100x (30,000 tasks) |
|---|---|---|---|
| openai/gpt-oss-120b (Groq, used in the eval) | $0.00071 | $0.21 | $21.42 |
| gpt-4o-mini (OpenAI) | $0.00071 | $0.21 | $21.42 |
| gpt-4.1-mini (OpenAI) | $0.00190 | $0.57 | $57.11 |

**Assumptions.** Today = one person triaging 10 tasks a day; 100x = 1,000 tasks a day. Token use per task stays as measured on our 41 scenarios (real inboxes are bigger, so input tokens would grow with the number and length of emails: the input is most of the cost). No caching, no retries billed beyond the measured ones.
**What breaks first:** not the bill but the rate limit. Groq's free tier for this model allows 8,000 tokens per minute and 200,000 per day (about 60 tasks at 3.5k tokens, or one full 41-scenario eval run per key per day). 100x needs a paid tier. Per-task time (several model calls in a row) also means one worker handles about one task every 5 to 10 s.
**Cost control in the agent itself:** `MAX_STEPS` = 12 and `MAX_COST_USD` = $0.05 per task, so a runaway task is capped at 12 calls (measured max cost of any eval task is far below the cap).
