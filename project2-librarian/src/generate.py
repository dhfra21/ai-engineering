"""Answer a question from retrieved chunks, with a citation for every claim."""
import re
import time

import httpx

from . import config
from .retrieve import get_retriever

SYSTEM = """You are a legal librarian for Tunisian law (Journal Officiel, laws 2013-2026).
Answer ONLY from the numbered sources below. Rules:
- Every sentence of your answer must end with the citation(s) of the source(s) it comes from, like [1] or [2][3].
- Give the complete answer: include every condition, exception, penalty, amount, breakdown, deadline and further obligation the sources attach to what was asked, not only the main fact.
- Write the whole answer in the language of the question: French question, French answer; Arabic question, Arabic answer. Do this even when the sources are in the other language.
- Quote article numbers and law numbers exactly as they appear in the sources.
- If the sources do not contain the answer, reply exactly: I don't know / لا أعرف / Je ne sais pas (in the question's language) and nothing else.
- Never use outside knowledge, and never invent an article or law number."""

IDK = ("I don't know", "لا أعرف", "Je ne sais pas")
_ARABIC = re.compile("[؀-ۿ]")


def idk_for(question):
    """The abstention phrase in the question's language (Arabic if it has Arabic letters, else French)."""
    return IDK[1] if _ARABIC.search(question) else IDK[2]


def build_prompt(question, chunks):
    sources = "\n\n".join(f"[{i}] {c['text']}" for i, c in enumerate(chunks, 1))
    return f"Sources:\n{sources}\n\nQuestion: {question}"


def chat(messages, model=None, max_tokens=500, retries=4):
    model = model or config.GENERATOR
    body = {"model": model, "messages": messages, "temperature": 0}
    # OpenAI's newer models want max_completion_tokens and some reject temperature
    body["max_completion_tokens" if config.PROVIDER == "openai" else "max_tokens"] = max_tokens
    for attempt in range(retries):
        r = httpx.post(config.LLM_URL, timeout=60, json=body,
                       headers={"Authorization": f"Bearer {config.api_key()}"})
        if r.status_code == 400 and "temperature" in r.text and "temperature" in body:
            body.pop("temperature")
            continue
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(2 ** attempt)
            continue
        r.raise_for_status()
        data = r.json()
        u = data["usage"]
        return data["choices"][0]["message"]["content"], {
            "prompt_tokens": u["prompt_tokens"], "completion_tokens": u["completion_tokens"],
            "cost_usd": config.cost_usd(model, u["prompt_tokens"], u["completion_tokens"])}
    raise RuntimeError("LLM API rate limit / server error after retries")


def answer(question, mode="hybrid+rerank", k=5, strategy="article", model=None, retriever=None,
           min_score=None, lang=None, year=None, **search_kw):
    """Full online pipeline. Returns answer text, cited chunks and per-stage timings/cost.

    search_kw goes to Retriever.search (n_candidates, skip_rerank_gap).
    """
    retriever = retriever or get_retriever(strategy)
    t0 = time.perf_counter()
    hits = retriever.search(question, mode=mode, k=k, lang=lang, year=year, **search_kw)
    t_search = time.perf_counter() - t0
    if not hits or (min_score is not None and hits[0]["score"] < min_score):
        return {"answer": idk_for(question), "abstained": True, "citations": [], "hits": hits,
                "latency": {"search": t_search, "generate": 0.0, "total": t_search}, "usage": {"cost_usd": 0.0}}
    t1 = time.perf_counter()
    text, usage = chat([{"role": "system", "content": SYSTEM},
                        {"role": "user", "content": build_prompt(question, hits)}], model=model)
    t_gen = time.perf_counter() - t1
    cited = sorted({int(n) for n in re.findall(r"\[(\d+)\]", text) if 1 <= int(n) <= len(hits)})
    abstained = any(p in text for p in IDK) and not cited
    if abstained and len(text.strip(" .\n")) <= 20:
        text = idk_for(question)   # the model sometimes refuses in the wrong language: always use the question's
    return {"answer": text, "abstained": abstained, "citations": [hits[i - 1] for i in cited], "cited": cited, "hits": hits,
            "latency": {"search": t_search, "generate": t_gen, "total": t_search + t_gen}, "usage": usage}
