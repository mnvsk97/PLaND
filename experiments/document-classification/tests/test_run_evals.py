import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_evals.py"
SPEC = importlib.util.spec_from_file_location("run_evals", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class RunEvalsTests(unittest.TestCase):
    def test_parse_prediction(self):
        labels = {"email", "presentation"}
        self.assertEqual(MODULE.parse_prediction('{"label":"email","confidence":0.8}', labels), ("email", 0.8, None))
        self.assertEqual(MODULE.parse_prediction('{"label":"presentation","confidence":0.8}', labels), ("presentation", 0.8, None))
        self.assertEqual(MODULE.parse_prediction('{"label":"other","confidence":0.8}', labels)[2], "invalid_label")
        self.assertEqual(MODULE.parse_prediction("email", labels)[2], "invalid_json")

    def test_aggregate(self):
        cases = [
            {"latency_seconds": 1.0, "correct": True, "expected": "email", "actual": "email", "error": None, "input_tokens": 10, "output_tokens": 2, "total_tokens": 12},
            {"latency_seconds": 2.0, "correct": False, "expected": "memo", "actual": "email", "error": None, "input_tokens": 11, "output_tokens": 2, "total_tokens": 13},
        ]
        result = MODULE.aggregate(cases)
        self.assertEqual(result["accuracy"], 0.5)
        self.assertEqual(result["total_tokens"], 25)
        self.assertEqual(result["confusion"]["memo"], {"email": 1})

    def test_sop_snapshot_records_content_hash_and_step_types(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skill = root / "skills" / "workflow" / "SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text(
                "---\nname: workflow\ndescription: test\n---\n\n"
                "1. Decide semantically. <!-- pland:english -->\n"
                "2. Read [rules](references/rules.md). <!-- pland:reference -->\n"
                "3. Run `python3 scripts/parse.py`. <!-- pland:command -->\n",
                encoding="utf-8",
            )
            result = MODULE.sop_snapshot(root)
            self.assertEqual(
                result["step_representations"],
                {"total": 3, "english": 1, "reference": 1, "command": 1},
            )
            self.assertEqual(result["explicitly_annotated_steps"], 3)
            self.assertEqual(result["variant"], "hybrid")
            self.assertEqual(len(result["sha256"]), 64)

    def test_frozen_invariants_ignore_only_sop_tool_wiring(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            (root / "instructions.md").write_text("Frozen prompt", encoding="utf-8")
            (root / "data" / "manifest.json").write_text(
                '{"sources":[{"path":"doc.txt","sha256":"abc"}]}', encoding="utf-8"
            )
            evals = root / "evals.csv"
            evals.write_text("input,output,reasoning\ndoc.txt,email,test\n", encoding="utf-8")
            first = (
                "from tools.datasources import read_datasource\n"
                "agent = create_deep_agent(model=MODEL, tools=[read_datasource], skills=['/skills/'])\n"
            )
            second = (
                "from tools.datasources import compact_datasource\n"
                "agent = create_deep_agent(model=MODEL, tools=[compact_datasource], skills=['/skills/'])\n"
            )
            (root / "agent.py").write_text(first, encoding="utf-8")
            _, first_invariants = MODULE.frozen_invariants(root, evals)
            (root / "agent.py").write_text(second, encoding="utf-8")
            _, second_invariants = MODULE.frozen_invariants(root, evals)
            self.assertEqual(
                first_invariants["agent_harness_sha256"],
                second_invariants["agent_harness_sha256"],
            )
            (root / "agent.py").write_text(second.replace("'/skills/'", "'/changed/'"), encoding="utf-8")
            _, changed = MODULE.frozen_invariants(root, evals)
            self.assertNotEqual(
                first_invariants["agent_harness_sha256"], changed["agent_harness_sha256"]
            )


if __name__ == "__main__":
    unittest.main()
