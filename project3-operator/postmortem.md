# Postmortem

What went wrong in Project 3, what it cost, and what we would do differently. Written 17 Nov 2026.

## 1. The API key ran out and the setup hid it

The course OpenAI key had no credits left (`credit_balance_exhausted`, HTTP 429), probably used up by Project 2.
Two things made it slower to find: the `.env` file had the key as `OPENAI API KEY : sk-...` (not `NAME=value`), so
python-dotenv could not read it and the error looked like a missing key; and a 429 looks like a rate limit, so the first
retry logic just waited. **Fix:** the loop now tells quota exhaustion apart from a rate limit, and `.env.example` shows
the exact format. **Lesson:** test one real API call before writing any eval code.

## 2. The free replacement had its own limits

We switched to Groq's free tier. The model we picked first (`llama-3.3-70b-versatile`) was not available on our account
(`model_not_found`); we listed the account's models and used `openai/gpt-oss-120b`. The free tier's rate limit then
broke the first full run: 10 of 37 scenarios failed with 429 after 6 retries. **Fix:** retry up to 12 times honouring
`Retry-After`, one worker, and a `--resume` flag that redoes only the errored scenarios. **Consequence:** wall-clock times
in the eval include rate-limit waits, so we also record `api_seconds` (time inside successful model calls only).

Third limit, found late: Groq also caps this model at **200,000 tokens per day**, and one full 41-scenario run is about
145k tokens. We had told ourselves the cap was 1,000 requests a day, so we launched repeat runs that silently retried
against a quota that was already empty; one hung for over an hour with no output. **Fix:** a daily-limit 429 now fails at
once with the reset time, the runner prints one line per scenario and saves partial results, and there is a `--category`
filter for cheap partial runs. The corrected injection scenarios could not be re-run before the freeze; see `threat_model.md`.
**Lesson:** read the provider's real limits before planning runs, and never run a long job whose progress you cannot see.

## 3. Our stop rule was too eager and punished the correct recovery

The first version stopped after 2 identical tool calls in a row ("stuck"). A scripted test of *recovery after failure*
showed the flaw: after a tool error, the right move is to retry the same call, and the rule killed the run. **Fix:** a
call counts as repeated only if its result is also identical, and we allow 3. A test for each case is in `tests/`.
**Lesson:** a safety limit needs a test for the behaviour it must not block, not only for the one it must stop.

## 4. One of our own scenarios was wrong

Scenario s29 simulates a tool that stays down. We first required the labels to be applied, which is impossible and
contradicts the point of the scenario (stop cleanly, damage nothing). We fixed the scenario, not the agent, and we
say so here because it moved the first baseline from 95% to 97%. The same run showed a real gap: a stuck run ended with
an empty final answer, so the user would not know why. The loop now always explains an early stop.

## 5. Our injection tests did not test injection

After the first full run, every injection scenario passed. Reading the trajectories showed why: in 7 of 11 the agent
labelled the email from the sender and subject in `list_emails` and **never opened the malicious body**. "0 attacks
succeeded" meant "0 attacks were seen". We rewrote the tasks to say "Read email N, then ..." and added an `exposed`
metric (did the agent read the malicious body?) so the injection result is reported only over runs where the attack
was actually in front of the model. **Lesson:** a defence is only measured when the attack reaches it.

## 6. The model missed an email and said it was done

In the first baseline, a triage task (s08) handled 5 of 6 target emails and the model's summary still claimed it was
complete. We changed the system prompt (go through every matching email; say exactly what you changed). The next run
passed. Honest caveat: s08 was in the test set when we tuned the prompt for it, so that gain is partly fitted to the
test; the scenarios are also ones we wrote, and the model scores near the ceiling, so the eval is likely easier than a
live audience. More and harder scenarios would be the next improvement.

## 7. What we did not do

- **No multi-turn user changes** ("actually, don't"): the agent takes one instruction per run. Listed as out of scope in `errors.md`.
- **No real mail server, no real accounts.** `send_draft` writes a row in a `sent` table.
- **One model, run a few times.** We did not compare models; runs on a free tier are noisy and variance is reported in the report.
- **Prices** in the cost model are list prices quoted from memory of the pricing pages and must be re-checked before quoting.

## What we would do differently

Make a real API call and a tiny end-to-end run on day one; write the stop rule *and its counter-test* first; read the
trajectories of passing runs, not only failing ones; and give the eval at least one scenario per attack where we can
prove the attack text reached the model.
