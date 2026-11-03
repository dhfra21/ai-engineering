"""The Librarian as a web service.

  uvicorn src.service:app --host 0.0.0.0 --port 8000

POST /ask       {"question": "..."}                       -> answer + citations + latency + cost
POST /feedback  {"request_id": "...", "vote": "up|down"}  -> appended to logs/feedback.jsonl
GET  /          a small page for asking questions (right-to-left for Arabic)
GET  /health
Every request is logged to logs/requests.jsonl (question, timings, tokens, cost) for the cost model.
"""
import json
import os
import threading
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel, Field

from . import generate
from .retrieve import get_retriever

LOGS = Path(os.getenv("LOG_DIR", Path(__file__).resolve().parents[1] / "logs"))
MODE = os.getenv("SEARCH_MODE", "hybrid+rerank")
TOP_K = int(os.getenv("TOP_K", "5"))
INDEX = os.getenv("INDEX", "article-oai")        # which index to serve (the deployed one uses OpenAI embeddings)
N_CANDIDATES = int(os.getenv("N_CANDIDATES", "30"))
SKIP_RERANK_GAP = float(os.environ["SKIP_RERANK_GAP"]) if os.getenv("SKIP_RERANK_GAP") else None
ABSTAIN_SCORE = float(os.environ["ABSTAIN_SCORE"]) if os.getenv("ABSTAIN_SCORE") else None
CACHE_ON = os.getenv("CACHE_ANSWERS", "0") == "1"   # off by default so the baseline is measurable
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")               # protects /admin/export; unset = endpoint disabled

app = FastAPI(title="The Librarian: Tunisian law Q&A")


@app.on_event("startup")
def _warm_up():
    """Load the index and models once, so the first user does not wait for them."""
    if os.getenv("WARM_UP", "1") == "1":
        get_retriever(INDEX)
        get_retriever(INDEX).search("test", mode=MODE, k=1)

_lock = threading.Lock()
_cache = {}


class Ask(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    lang: str | None = Field(default=None, pattern="^(ar|fr)$")
    year: int | None = None


class Feedback(BaseModel):
    request_id: str
    vote: str = Field(pattern="^(up|down)$")
    comment: str = Field(default="", max_length=500)


def _log(name, record):
    LOGS.mkdir(parents=True, exist_ok=True)
    with _lock, (LOGS / name).open("a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


@app.get("/health")
def health():
    return {"status": "ok", "index": INDEX, "mode": MODE, "k": TOP_K, "model": generate.config.GENERATOR}


@app.post("/ask")
def ask(req: Ask):
    rid = uuid.uuid4().hex[:12]
    key = (req.question.strip(), req.lang, req.year)
    cached = CACHE_ON and key in _cache
    t0 = time.perf_counter()
    if cached:
        out = _cache[key]
    else:
        try:
            out = generate.answer(req.question, mode=MODE, k=TOP_K, strategy=INDEX, min_score=ABSTAIN_SCORE,
                                  lang=req.lang, year=req.year, n_candidates=N_CANDIDATES,
                                  skip_rerank_gap=SKIP_RERANK_GAP)
        except RuntimeError as e:  # missing key, rate limit
            raise HTTPException(503, str(e))
        if CACHE_ON:
            _cache[key] = out
    total = time.perf_counter() - t0
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0} if cached else out["usage"]
    numbers = out.get("cited") or range(1, len(out["citations"]) + 1)   # the [n] used in the answer text
    cites = [{"n": n, "ref": c["ref"], "article": c["article"], "lang": c["lang"], "text": c["text"]}
             for n, c in zip(numbers, out["citations"])]
    _log("requests.jsonl", {"request_id": rid, "ts": time.time(), "question": req.question, "abstained": out["abstained"],
                            "cached": cached, "latency": out["latency"], "total_s": total, "usage": usage,
                            "retrieved": [h["id"] for h in out["hits"]]})
    return {"request_id": rid, "answer": out["answer"], "abstained": out["abstained"], "citations": cites,
            "latency_s": round(total, 3), "cost_usd": usage.get("cost_usd", 0.0), "cached": cached}


@app.post("/feedback")
def feedback(fb: Feedback):
    _log("feedback.jsonl", {"ts": time.time(), **fb.model_dump()})
    return {"ok": True}


@app.get("/admin/export", response_class=PlainTextResponse)
def export(what: str = "feedback", authorization: str | None = Header(default=None)):
    """Download the logs (JSON lines): feedback or requests. Needs 'Authorization: Bearer <ADMIN_TOKEN>'."""
    if not ADMIN_TOKEN or authorization != f"Bearer {ADMIN_TOKEN}":
        raise HTTPException(403, "forbidden")
    f = LOGS / {"feedback": "feedback.jsonl", "requests": "requests.jsonl"}.get(what, "feedback.jsonl")
    return f.read_text() if f.exists() else ""


PAGE = """<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>The Librarian</title>
<style>
body{font-family:system-ui,sans-serif;max-width:760px;margin:2rem auto;padding:0 1rem;color:#222}
textarea{width:100%;font-size:1.05rem;padding:.6rem;box-sizing:border-box}
button{font-size:1rem;padding:.5rem 1rem;margin:.4rem .3rem 0 0;cursor:pointer}
.answer{background:#f4f6f8;padding:1rem;border-radius:8px;margin-top:1rem;white-space:pre-wrap}
.cite{border-left:3px solid #8aa;padding:.3rem .8rem;margin:.6rem 0;font-size:.92rem;color:#444}
.meta{color:#777;font-size:.85rem;margin-top:.5rem}
</style>
<h1>The Librarian</h1>
<p>Ask about Tunisian laws (Journal Officiel 2013–2026), in Arabic or French. / اسأل عن القوانين التونسية بالعربية أو بالفرنسية.</p>
<textarea id="q" rows="3" dir="auto" placeholder="Question… / السؤال…"></textarea>
<button onclick="ask()">Ask / اسأل</button>
<div id="out"></div>
<script>
let rid=null;
async function ask(){
  const q=document.getElementById('q').value.trim(); if(q.length<3) return;
  const out=document.getElementById('out'); out.textContent='…';
  const r=await fetch('/ask',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({question:q})});
  if(!r.ok){out.textContent='Error '+r.status+': '+(await r.json()).detail; return;}
  const d=await r.json(); rid=d.request_id;
  out.innerHTML='';
  const a=document.createElement('div'); a.className='answer'; a.dir='auto'; a.textContent=d.answer; out.append(a);
  d.citations.forEach((c,i)=>{const e=document.createElement('div'); e.className='cite'; e.dir='auto';
    e.textContent='['+c.n+'] '+c.text.slice(0,500)+(c.text.length>500?'…':''); out.append(e);});
  const m=document.createElement('div'); m.className='meta'; m.textContent=d.latency_s+' s · $'+d.cost_usd.toFixed(5); out.append(m);
  for(const v of ['up','down']){const b=document.createElement('button'); b.textContent=v==='up'?'👍':'👎';
    b.onclick=async()=>{await fetch('/feedback',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({request_id:rid,vote:v})}); out.append(' Merci / شكرا');}; out.append(b);}
}
const preset=new URLSearchParams(location.search).get('q');
if(preset){document.getElementById('q').value=preset; ask();}
</script></html>"""


@app.get("/", response_class=HTMLResponse)
def index():
    return PAGE
