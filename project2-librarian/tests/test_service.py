import json

import pytest
from fastapi.testclient import TestClient

from src import service

CHUNK = {"id": "law-1-1:fr:0", "doc_id": "law-1-1", "lang": "fr", "year": 2020, "number": 1, "ref": "Loi n° 2020-1",
         "article": "Art. 1", "text": "Loi n° 2020-1 — Art. 1\nArt. 1 - Texte.", "score": 1.0}


def fake_answer(question, **kw):
    return {"answer": "Réponse [1]", "abstained": False, "citations": [CHUNK], "hits": [CHUNK],
            "latency": {"search": 0.1, "generate": 0.2, "total": 0.3},
            "usage": {"prompt_tokens": 100, "completion_tokens": 20, "cost_usd": 0.0002}}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(service, "LOGS", tmp_path)
    monkeypatch.setattr(service.generate, "answer", fake_answer)
    service._cache.clear()
    monkeypatch.setenv("WARM_UP", "0")
    return TestClient(service.app)


def test_ask_returns_answer_and_logs(client, tmp_path):
    r = client.post("/ask", json={"question": "Quel est le délai ?"})
    assert r.status_code == 200
    d = r.json()
    assert d["answer"] == "Réponse [1]" and d["citations"][0]["ref"] == "Loi n° 2020-1" and d["citations"][0]["n"] == 1 and d["cost_usd"] == 0.0002
    logged = json.loads((tmp_path / "requests.jsonl").read_text().splitlines()[0])
    assert logged["request_id"] == d["request_id"] and logged["usage"]["cost_usd"] == 0.0002


def test_feedback_is_stored(client, tmp_path):
    rid = client.post("/ask", json={"question": "Une question ?"}).json()["request_id"]
    assert client.post("/feedback", json={"request_id": rid, "vote": "down"}).json() == {"ok": True}
    assert json.loads((tmp_path / "feedback.jsonl").read_text())["vote"] == "down"


def test_bad_input_is_rejected(client):
    assert client.post("/ask", json={"question": "a"}).status_code == 422
    assert client.post("/feedback", json={"request_id": "x", "vote": "maybe"}).status_code == 422


def test_cache_skips_the_llm_and_the_cost(client, monkeypatch):
    monkeypatch.setattr(service, "CACHE_ON", True)
    first = client.post("/ask", json={"question": "Même question ?"}).json()
    second = client.post("/ask", json={"question": "Même question ?"}).json()
    assert not first["cached"] and second["cached"] and second["cost_usd"] == 0.0


def test_missing_key_gives_503(client, monkeypatch):
    def boom(q, **kw):
        raise RuntimeError("OPENAI_API_KEY is not set")
    monkeypatch.setattr(service.generate, "answer", boom)
    assert client.post("/ask", json={"question": "Une question ?"}).status_code == 503


def test_page_and_health(client):
    assert "The Librarian" in client.get("/").text
    assert client.get("/health").json()["status"] == "ok"


def test_admin_export_needs_the_token(client, monkeypatch):
    client.post("/ask", json={"question": "Une question ?"})
    assert client.get("/admin/export?what=requests").status_code == 403           # disabled without a token
    monkeypatch.setattr(service, "ADMIN_TOKEN", "s3cret")
    assert client.get("/admin/export?what=requests", headers={"Authorization": "Bearer nope"}).status_code == 403
    r = client.get("/admin/export?what=requests", headers={"Authorization": "Bearer s3cret"})
    assert r.status_code == 200 and "Une question ?" in r.text
