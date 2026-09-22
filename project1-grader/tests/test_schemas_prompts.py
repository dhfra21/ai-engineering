import unittest

from harness import prompts, schemas
from harness.config import PROMPTS_DIR


class TestSchemas(unittest.TestCase):
    def test_valid_judge(self):
        schemas.validate({"reason": "ok", "failed_criteria": [], "grade": "good"}, schemas.JUDGE)

    def test_rejects(self):
        bad = [
            {"reason": "x", "failed_criteria": [], "grade": "great"},          # enum
            {"reason": "x", "grade": "good"},                                   # missing
            {"reason": "x", "failed_criteria": ["tone"], "grade": "bad"},       # item enum
            {"reason": "x", "failed_criteria": [], "grade": "good", "k": 1},    # extra key
            {"reason": " ", "failed_criteria": [], "grade": "good"},            # empty
        ]
        for value in bad:
            with self.assertRaises(schemas.SchemaError, msg=value):
                schemas.validate(value, schemas.JUDGE)

    def test_strict_mode_shape(self):
        # Groq strict mode: every property required, no additional properties.
        for name, s in schemas.BY_NAME.items():
            self.assertEqual(set(s["required"]), set(s["properties"]), name)
            self.assertIs(s["additionalProperties"], False, name)


class TestPrompts(unittest.TestCase):
    def test_every_prompt_file_loads_and_renders(self):
        files = sorted(PROMPTS_DIR.glob("*/*.md"))
        self.assertTrue(files)
        for path in files:
            p = prompts.load(path.parent.name, path.stem)
            names = set(prompts._PLACEHOLDER.findall(p.system + p.user))
            msgs = p.render(**{n: f"<{n}>" for n in names})
            self.assertEqual([m["role"] for m in msgs], ["system", "user"])
            self.assertNotIn("{{", msgs[0]["content"] + msgs[1]["content"], path)

    def test_render_rejects_missing_and_unknown(self):
        p = prompts.load("system", "v1")
        with self.assertRaises(KeyError):
            p.render(sql="SELECT 1")
        with self.assertRaises(KeyError):
            p.render(sql="SELECT 1", schema="s", surprise="x")


if __name__ == "__main__":
    unittest.main()
