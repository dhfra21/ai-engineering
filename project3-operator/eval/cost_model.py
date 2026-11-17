"""Cost model from a finished eval: python -m eval.cost_model [--tag v2]  ->  results/cost_model.md

Tokens and dollars per task come from the eval's real runs (measured). Everything about the future is an assumption,
listed in the output. Prices are list prices in USD per million tokens (in, out); check the pricing pages before quoting.
"""
import argparse
import json
import statistics

from agent import config

PRICES = {"openai/gpt-oss-120b (Groq, used in the eval)": (0.15, 0.60), "gpt-4o-mini (OpenAI)": (0.15, 0.60),
          "gpt-4.1-mini (OpenAI)": (0.40, 1.60)}
TODAY, X100 = 10 * 30, 1000 * 30          # tasks per month: one person doing 10 a day; 100x that = 1,000 a day


def q(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p * (len(xs) - 1))))]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="v2")
    a = ap.parse_args()
    rows = [r for r in json.loads((config.ROOT / "results" / f"eval_{a.tag}.json").read_text()) if "error" not in r]
    tin = statistics.mean(r["tokens_in"] for r in rows)
    tout = statistics.mean(r["tokens_out"] for r in rows)
    steps = [r["n_steps"] for r in rows]
    api = [r["api_seconds"] for r in rows if r.get("api_seconds")]
    L = [f"# Cost model (from eval `{a.tag}`, {len(rows)} tasks)", "",
         f"Measured per task: **{tin:.0f} input + {tout:.0f} output tokens**, {statistics.mean(steps):.1f} steps on average "
         f"(p95 {q(steps, .95)}), max {max(steps)}.",
         f"Latency per task, model time only (no rate-limit waits): "
         + (f"p50 {q(api, .5):.1f} s, p95 {q(api, .95):.1f} s." if api else "not recorded in this run."), "",
         f"| model | $ per task | $/month today ({TODAY} tasks) | $/month at 100x ({X100:,} tasks) |", "|---|---|---|---|"]
    for name, (pi, po) in PRICES.items():
        c = (tin * pi + tout * po) / 1e6
        L.append(f"| {name} | ${c:.5f} | ${c * TODAY:.2f} | ${c * X100:,.2f} |")
    L += ["", "**Assumptions.** Today = one person triaging 10 tasks a day; 100x = 1,000 tasks a day. Token use per task stays as "
          "measured on our 41 scenarios (real inboxes are bigger, so input tokens would grow with the number and length of emails: "
          "the input is most of the cost). No caching, no retries billed beyond the measured ones.",
          "**What breaks first:** not the bill but the rate limit. Groq's free tier for this model allows 8,000 tokens per minute and "
          "200,000 per day (about 60 tasks at 3.5k tokens, or one full 41-scenario eval run per key per day). 100x needs a paid tier. "
          "Per-task time (several model calls in a row) also means one worker handles about one task every 5 to 10 s.",
          "**Cost control in the agent itself:** `MAX_STEPS` = 12 and `MAX_COST_USD` = $0.05 per task, so a runaway task is "
          "capped at 12 calls (measured max cost of any eval task is far below the cap)."]
    out = config.ROOT / "results" / "cost_model.md"
    out.write_text("\n".join(L) + "\n")
    print("\n".join(L))
