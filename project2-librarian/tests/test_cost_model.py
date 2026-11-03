import json

import pytest

from eval.cost_model import load_rows, model, to_markdown

ROWS = [{"cost": 0.0002, "latency": 8.0, "abstained": False}, {"cost": 0.0004, "latency": 10.0, "abstained": False},
        {"cost": 0.0, "latency": 6.0, "abstained": True}]
PARAMS = dict(query_tokens=25, today_per_day=100, factor=100, utilisation=0.25, worker_usd_month=30.0)


def test_per_request_cost_adds_the_embedding_call_only_for_openai_indexes():
    oai = model(ROWS, {"backend": "openai", "embed_cost_usd": 0.135})
    local = model(ROWS, {"backend": "e5"})
    assert oai["gen_usd"] == pytest.approx(0.0002)
    assert oai["embed_usd"] == pytest.approx(25 * 0.02 / 1e6) and local["embed_usd"] == 0
    assert oai["index_build_usd"] == 0.135


def test_scenarios_scale_with_traffic_and_need_more_workers():
    m = model(ROWS, {"backend": "e5"})
    today, big = m["scenarios"]
    assert big["per_day"] == 100 * today["per_day"]
    assert big["fees_month"] == pytest.approx(100 * today["fees_month"])
    assert today["workers"] == 1 and big["workers"] > 1 and big["hosting_month"] == big["workers"] * 30


def test_loads_service_log_and_eval_report(tmp_path):
    log = tmp_path / "requests.jsonl"
    log.write_text(json.dumps({"usage": {"cost_usd": 0.1}, "total_s": 2.0, "abstained": False}) + "\n")
    assert load_rows(log) == [{"cost": 0.1, "latency": 2.0, "abstained": False}]
    rep = tmp_path / "r.json"
    rep.write_text(json.dumps({"rows": [{"gen_cost": 0.2, "latency": {"total": 3.0}, "abstained": True}]}))
    assert load_rows(rep) == [{"cost": 0.2, "latency": 3.0, "abstained": True}]


def test_markdown_states_its_assumptions():
    text = to_markdown(model(ROWS, {"backend": "e5"}), "test", PARAMS)
    assert "Assumptions" in text and "Total per request" in text and "100x" in text
