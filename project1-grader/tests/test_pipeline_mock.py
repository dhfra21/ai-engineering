"""End-to-end smoke test of every command on the mock backend, in a temporary
copy of the project (so it never touches the real data/ or results/).
Labels are synthetic and exist only to exercise the code paths."""
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class TestPipelineMock(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        for name in ("db", "data", "harness", "prompts"):
            shutil.copytree(ROOT / name, self.tmp / name,
                            ignore=shutil.ignore_patterns("store.db", "candidates.jsonl", "golden.jsonl",
                                                          "*.jsonl.bak", "__pycache__"))
        for f in (self.tmp / "data" / "labels").glob("*.jsonl"):
            f.unlink()
        self.env = {**os.environ, "GRADER_BACKEND": "mock", "GROQ_API_KEY": ""}

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def sh(self, *args):
        out = subprocess.run([sys.executable, *args], cwd=self.tmp, env=self.env,
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)
        return out.stdout

    def test_full_pipeline(self):
        self.sh("db/build_db.py")
        self.sh("data/make_queries.py")
        self.sh("-m", "harness.candidates")
        cands = [json.loads(l) for l in (self.tmp / "data" / "candidates.jsonl").read_text().splitlines()]
        self.assertGreaterEqual(len(cands), 150)

        rng = random.Random(0)
        labels = self.tmp / "data" / "labels"
        for name in ("a", "b"):
            with (labels / f"{name}.jsonl").open("w") as f:
                for c in cands:
                    g = rng.choice(["good", "bad"])
                    f.write(json.dumps({"item_id": c["id"], "labeller": name, "grade": g,
                                        "failed_criteria": ["correct"] if g == "bad" else [], "note": ""}) + "\n")
        self.sh("-m", "harness.golden", "--a", "a", "--b", "b")
        adj = [json.loads(l) for l in (labels / "adjudication.jsonl").read_text().splitlines()]
        for r in adj:
            r["final"], r["reason"] = "bad", "test"
            r["final_failed_criteria"] = ["clear"]
        (labels / "adjudication.jsonl").write_text("".join(json.dumps(r) + "\n" for r in adj))
        self.sh("-m", "harness.golden", "--a", "a", "--b", "b")
        golden = (self.tmp / "data" / "golden.jsonl").read_text().splitlines()
        self.assertEqual(len(golden), len(cands))

        self.sh("-m", "harness.run", "--split", "dev")
        out = self.sh("-m", "harness.run", "--split", "dev")
        self.assertIn("vs previous run", out)
        run_dir = next((self.tmp / "results" / "mock" / "runs").iterdir())
        rows = [json.loads(l) for l in (run_dir / "per_item.jsonl").read_text().splitlines()]
        self.assertEqual(len(rows), 60)
        for r in rows:
            for key in ("input", "output", "score", "reason"):
                self.assertIn(key, r)

        self.sh("-m", "harness.judge_eval", "--split", "dev")
        self.sh("-m", "harness.bias", "position", "--split", "dev", "--limit", "5")
        self.sh("-m", "harness.bias", "verbosity", "--split", "dev", "--limit", "5")
        self.sh("-m", "harness.bias", "verbosity", "--split", "dev", "--limit", "5", "--pad", "llm")
        self.sh("-m", "harness.cost")
        self.assertFalse((self.tmp / "results" / "runs").exists(), "mock results leaked into results/")


if __name__ == "__main__":
    unittest.main()
