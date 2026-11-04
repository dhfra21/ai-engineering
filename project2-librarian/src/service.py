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
# Week 8 (optimisation.md): rerank 10 candidates instead of 30, p95 -52% for -2 points of correctness
N_CANDIDATES = int(os.getenv("N_CANDIDATES", "10"))
RERANK_MAX_LENGTH = int(os.getenv("RERANK_MAX_LENGTH", "384"))
SKIP_RERANK_GAP = float(os.environ["SKIP_RERANK_GAP"]) if os.getenv("SKIP_RERANK_GAP") else None
_abstain = os.getenv("ABSTAIN_SCORE", "")   # off: a score threshold refuses 74% of paraphrased answerable questions (results/threshold_check.md)
ABSTAIN_SCORE = float(_abstain) if _abstain else None
CACHE_ON = os.getenv("CACHE_ANSWERS", "0") == "1"   # off by default so the baseline is measurable
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")               # protects /admin/export; unset = endpoint disabled

app = FastAPI(title="The Librarian: Tunisian law Q&A")


@app.on_event("startup")
def _warm_up():
    """Load the index and models once, so the first user does not wait for them."""
    if os.getenv("WARM_UP", "1") == "1":
        get_retriever(INDEX, RERANK_MAX_LENGTH).search("test", mode=MODE, k=1)

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
                                  retriever=get_retriever(INDEX, RERANK_MAX_LENGTH),
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


PAGE = r"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>The Librarian · أمين المكتبة</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,800&family=Amiri:wght@400;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Sans+Arabic:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{--paper:#f5efe3;--paper-2:#efe6d4;--card:#fffdf8;--ink:#1d1b17;--ink-2:#5b554b;--rule:#d6cab3;--red:#b3122b;--red-soft:rgba(179,18,43,.08);--ok:#2f6b4f;
--display:'Fraunces',Georgia,serif;--ar:'Amiri','Noto Naskh Arabic',serif;--ui:'IBM Plex Sans','IBM Plex Sans Arabic',system-ui,sans-serif}
@media (prefers-color-scheme:dark){:root{--paper:#16140f;--paper-2:#1d1a14;--card:#211e17;--ink:#efe8da;--ink-2:#a69d8c;--rule:#3a3428;--red:#e0485e;--red-soft:rgba(224,72,94,.12);--ok:#6fbf95}}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--ui);font-size:16px;line-height:1.6;
background-image:radial-gradient(circle at 15% 0%,var(--paper-2),transparent 55%),repeating-linear-gradient(0deg,transparent 0 31px,rgba(120,100,60,.035) 31px 32px)}
.wrap{max-width:780px;margin:0 auto;padding:0 16px 64px}
[lang=ar],.ar{font-family:var(--ar)}
header{padding:40px 0 18px;text-align:center}
.kicker{font-size:.72rem;letter-spacing:.22em;text-transform:uppercase;color:var(--ink-2)}
h1{font-family:var(--display);font-weight:800;font-size:clamp(2.3rem,7vw,3.6rem);line-height:1;margin:.35em 0 .1em;letter-spacing:-.02em}
h1 .ar{font-weight:700;font-size:.72em;color:var(--red);margin-inline-start:.25em}
.rules{border-top:3px double var(--ink);border-bottom:1px solid var(--ink);height:6px;margin:16px 0 10px}
.lede{display:flex;justify-content:space-between;gap:16px;font-size:.92rem;color:var(--ink-2);flex-wrap:wrap}
.lede p{margin:0;flex:1 1 280px}.lede p.ar{text-align:right;font-size:1.08rem}
form{margin-top:26px;background:var(--card);border:1px solid var(--rule);border-radius:4px;box-shadow:0 1px 0 var(--rule),0 18px 40px -28px rgba(60,40,10,.45)}
textarea{display:block;width:100%;min-height:96px;resize:vertical;border:0;background:transparent;color:var(--ink);padding:18px 20px 8px;font:1.12rem/1.55 var(--display);outline:none}
textarea:dir(rtl){font-family:var(--ar);font-size:1.3rem}
.bar{display:flex;align-items:center;gap:10px;padding:10px 12px 12px 20px;border-top:1px dashed var(--rule);flex-wrap:wrap}
.hint{font-size:.78rem;color:var(--ink-2);margin-inline-end:auto}
kbd{font:inherit;border:1px solid var(--rule);border-bottom-width:2px;border-radius:3px;padding:0 4px}
.ask{appearance:none;border:0;background:var(--ink);color:var(--paper);font:600 .95rem var(--ui);padding:10px 20px;border-radius:3px;cursor:pointer;transition:transform .15s,background .15s;margin-inline-start:auto}
.ask:hover{background:var(--red)}.ask:active{transform:translateY(1px)}.ask:disabled{opacity:.5;cursor:wait}
.chips{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0 0}
.chip{border:1px solid var(--rule);background:transparent;color:var(--ink-2);border-radius:999px;padding:5px 12px;font:.82rem var(--ui);cursor:pointer;transition:all .15s;text-align:start}
.chip:hover{border-color:var(--red);color:var(--red)}.chip.ar{font:1rem var(--ar)}
.chips span{font-size:.72rem;letter-spacing:.18em;text-transform:uppercase;color:var(--ink-2);align-self:center;margin-inline-end:4px}
#out{margin-top:30px}
.loading{height:3px;background:linear-gradient(90deg,transparent,var(--red),transparent);background-size:40% 100%;background-repeat:no-repeat;animation:sweep 1.1s ease-in-out infinite}
.loading-t{font-size:.85rem;color:var(--ink-2);margin-top:10px}
@keyframes sweep{from{background-position:-40% 0}to{background-position:140% 0}}
.notice{background:var(--card);border:1px solid var(--rule);border-top:4px solid var(--ink);padding:22px 24px 18px;border-radius:2px;animation:rise .45s ease-out both}
.notice h2{margin:0 0 10px;font:.72rem var(--ui);letter-spacing:.22em;text-transform:uppercase;color:var(--ink-2)}
.answer{font-family:var(--display);font-size:1.16rem;line-height:1.7;white-space:pre-wrap}
.answer[dir=rtl]{font-family:var(--ar);font-size:1.38rem;line-height:1.9}
.answer sup a{color:var(--red);text-decoration:none;font:600 .68em var(--ui);padding:0 1px}
.answer sup a:hover{text-decoration:underline}.answer sup{color:var(--red);font-size:.68em}.answer sup a{font-size:1em}
.notice.idk{border-top-color:var(--ink-2)}.notice.idk .answer{color:var(--ink-2);font-style:italic}
.scope{margin-top:12px;font-size:.86rem;color:var(--ink-2);border-inline-start:2px solid var(--rule);padding-inline-start:12px}
.scope[dir=rtl]{font-family:var(--ar);font-size:1rem}
.meta{display:flex;gap:14px;align-items:center;flex-wrap:wrap;margin-top:16px;padding-top:12px;border-top:1px solid var(--rule);font-size:.8rem;color:var(--ink-2)}
.meta .vote{margin-inline-start:auto;display:flex;gap:6px;align-items:center}
.vote button{border:1px solid var(--rule);background:transparent;border-radius:3px;padding:3px 10px;font-size:1rem;cursor:pointer;transition:all .15s}
.vote button:hover:not(:disabled){border-color:var(--ink)}.vote button:disabled{opacity:.35;cursor:default}.vote button.on{opacity:1;border-color:var(--ok);background:var(--red-soft)}
.cites{margin-top:26px;animation:rise .45s .1s ease-out both}
.cites h3{font:.72rem var(--ui);letter-spacing:.22em;text-transform:uppercase;color:var(--ink-2);margin:0 0 8px;display:flex;align-items:center;gap:10px}
.cites h3::after{content:"";flex:1;border-top:1px solid var(--rule)}
details{border-bottom:1px solid var(--rule);padding:10px 4px;transition:background .4s}
details.flash{background:var(--red-soft)}
summary{cursor:pointer;list-style:none;display:grid;grid-template-columns:2.2em 1fr auto;gap:2px 8px;align-items:baseline}
summary::-webkit-details-marker{display:none}
.num{font:700 .95rem var(--display);color:var(--red)}
.ref{font-weight:600}.ref[dir=rtl]{font-family:var(--ar);font-size:1.12rem}
.more{font-size:.75rem;color:var(--ink-2)}details[open] .more{visibility:hidden}
.excerpt{grid-column:2/4;font-size:.9rem;color:var(--ink-2);display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.excerpt[dir=rtl],.full[dir=rtl]{font-family:var(--ar);font-size:1.05rem}
details[open] .excerpt{display:none}
.full{margin:10px 0 4px 2.6em;white-space:pre-wrap;font-size:.92rem;max-height:340px;overflow:auto;padding-inline-end:8px}
.err{border:1px solid var(--red);color:var(--red);padding:12px 16px;border-radius:3px;background:var(--red-soft)}
footer{margin-top:56px;padding-top:14px;border-top:1px solid var(--rule);font-size:.78rem;color:var(--ink-2);display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}
footer a{color:inherit}
@keyframes rise{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
@media (max-width:520px){header{padding-top:26px}.hint{display:none}.full{margin-inline-start:0}}
</style></head><body><div class="wrap">
<header>
  <div class="kicker"><span dir="ltr">Journal Officiel · 2013–2026</span> · <span lang="ar" dir="rtl">الرائد الرسمي</span></div>
  <h1>The Librarian<span class="ar" lang="ar">أمين المكتبة</span></h1>
  <div class="rules"></div>
  <div class="lede">
    <p>Posez une question sur les lois tunisiennes publiées depuis 2013. Chaque réponse cite l'article d'où elle vient.</p>
    <p class="ar" lang="ar" dir="rtl">اطرح سؤالك حول القوانين التونسية المنشورة منذ 2013، وكل إجابة تذكر الفصل الذي استُخرجت منه.</p>
  </div>
</header>
<form id="f">
  <textarea id="q" dir="auto" maxlength="500" placeholder="Votre question… / سؤالك…" aria-label="Question"></textarea>
  <div class="bar"><span class="hint"><kbd>Ctrl</kbd> + <kbd>Entrée</kbd></span><button class="ask" id="go" type="submit">Demander · اسأل</button></div>
</form>
<div class="chips" id="chips"><span>Exemples</span>
  <button class="chip" type="button">Les contrôles antidopage doivent-ils être notifiés au sportif à l'avance ?</button>
  <button class="chip ar" type="button" lang="ar" dir="rtl">إلى من تقدم المحكمة الدستورية تقريرها السنوي ومتى؟</button>
  <button class="chip" type="button">Quelle amende pour un spectacle organisé sans respecter l'article 21 de la loi sur l'artiste ?</button>
</div>
<main id="out" aria-live="polite"></main>
<footer><span>Pas un avis juridique : seul le Journal Officiel fait foi. · ليست استشارة قانونية</span>
<a href="https://github.com/dhfra21/ai-engineering/tree/main/project2-librarian">Code &amp; méthode</a></footer>
</div>
<script>
const $=s=>document.querySelector(s), out=$('#out'), q=$('#q'), go=$('#go');
const AR=/[؀-ۿ]/, IDK=["I don't know","لا أعرف","Je ne sais pas"];
let rid=null;
function el(tag,cls,text){const e=document.createElement(tag); if(cls) e.className=cls; if(text!=null) e.textContent=text; return e;}
function dirOf(t){return AR.test(t)?'rtl':'ltr';}
function flash(n){const d=document.getElementById('c'+n); if(!d) return; d.open=true; d.scrollIntoView({behavior:'smooth',block:'center'});
  d.classList.remove('flash'); void d.offsetWidth; d.classList.add('flash'); setTimeout(()=>d.classList.remove('flash'),1600);}
// turn [n] into superscript links to the footnotes; text is only ever set with textContent
function answerNode(text,known){
  const p=el('div','answer'); p.dir=dirOf(text); let prevMark=false;
  text.split(/(\[\d+\])/).forEach(part=>{if(!part) return; const m=part.match(/^\[(\d+)\]$/);
    if(m&&known.has(+m[1])){const s=el('sup'),a=el('a',null,m[1]); a.href='#c'+m[1]; a.onclick=e=>{e.preventDefault();flash(m[1]);};
      if(prevMark) s.append(','); s.append(a); p.append(s); prevMark=true;}
    else {p.append(document.createTextNode(part)); prevMark=false;}});
  return p;}
async function vote(v,btns){btns.forEach(b=>b.disabled=true); btns[v==='up'?0:1].classList.add('on');
  try{await fetch('/feedback',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({request_id:rid,vote:v})});}catch(e){}
  btns[0].parentNode.append(el('span',null,'Merci · شكرا'));}
async function ask(){
  const text=q.value.trim(); if(text.length<3){q.focus(); return;}
  go.disabled=true; out.replaceChildren(el('div','loading'),el('div','loading-t',AR.test(text)?'جارٍ البحث في الرائد الرسمي…':'Recherche dans le Journal Officiel…'));
  history.replaceState(null,'','?q='+encodeURIComponent(text));
  try{
    const r=await fetch('/ask',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({question:text})});
    const d=await r.json().catch(()=>({}));
    if(!r.ok) throw new Error(typeof d.detail==='string'?d.detail:'Erreur '+r.status);
    rid=d.request_id; render(d,text);
  }catch(e){out.replaceChildren(el('div','err','Le service n’a pas pu répondre · تعذّرت الإجابة — '+e.message));}
  finally{go.disabled=false;}}
function render(d,question){
  const idk=d.abstained||IDK.includes(d.answer.trim()), ar=AR.test(question);
  const card=el('section','notice'+(idk?' idk':''));
  card.append(el('h2',null,idk?(ar?'لا توجد إجابة في المصادر':'Pas de réponse dans les sources'):(ar?'الإجابة':'Réponse')));
  const known=new Set(d.citations.map(c=>c.n)); card.append(answerNode(d.answer,known));
  if(idk){const s=el('div','scope',ar?'تغطي المكتبة القوانين المنشورة بالرائد الرسمي من 2013 إلى 2026 فقط، دون المجلات (مجلة الالتزامات والعقود، المجلة الجزائية…).'
    :'La bibliothèque couvre les lois publiées au Journal Officiel de 2013 à 2026, pas les codes (COC, Code pénal…). Reformulez, ou citez la loi.'); s.dir=ar?'rtl':'ltr'; card.append(s);}
  const meta=el('div','meta'); meta.append(el('span',null,d.latency_s.toFixed(1)+' s'),el('span',null,'$'+d.cost_usd.toFixed(5)));
  if(d.cached) meta.append(el('span',null,'cache'));
  const v=el('span','vote'), up=el('button',null,'👍'), down=el('button',null,'👎'); up.title='Utile · مفيد'; down.title='Pas utile · غير مفيد';
  up.onclick=()=>vote('up',[up,down]); down.onclick=()=>vote('down',[up,down]); v.append(up,down); meta.append(v); card.append(meta);
  const nodes=[card];
  if(d.citations.length){const box=el('section','cites'); box.append(el('h3',null,ar?'المصادر · Sources':'Sources · المصادر'));
    d.citations.forEach(c=>{const det=el('details'); det.id='c'+c.n; const sum=el('summary');
      const ref=el('span','ref',c.ref+(c.article?' — '+c.article:'')); ref.dir=c.lang==='ar'?'rtl':'ltr';
      const body=c.text.split('\n').slice(1).join('\n').trim()||c.text;
      const ex=el('span','excerpt',body); ex.dir=ref.dir;
      sum.append(el('span','num','['+c.n+']'),ref,el('span','more','lire · اقرأ'),ex);
      const full=el('div','full',body); full.dir=ref.dir; det.append(sum,full); box.append(det);});
    nodes.push(box);}
  out.replaceChildren(...nodes);}
$('#f').onsubmit=e=>{e.preventDefault(); ask();};
q.addEventListener('keydown',e=>{if(e.key==='Enter'&&(e.ctrlKey||e.metaKey)){e.preventDefault(); ask();}});
document.querySelectorAll('.chip').forEach(c=>c.onclick=()=>{q.value=c.textContent; ask();});
const preset=new URLSearchParams(location.search).get('q'); if(preset){q.value=preset; ask();}
</script></body></html>"""


@app.get("/", response_class=HTMLResponse)
def index():
    return PAGE
