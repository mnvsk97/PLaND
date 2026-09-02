import argparse
import importlib.util
import json
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

    def test_redact_trace_keeps_final_prediction_and_usage(self):
        trace = [
            {"content": "private document text", "usage": {"input_tokens": 3}, "tool_calls": []},
            {"content": '{"label":"email","confidence":0.8}', "usage": {"output_tokens": 2}},
        ]
        result = MODULE.redact_trace(trace)
        self.assertIsNone(result[0]["content"])
        self.assertTrue(result[0]["content_redacted"])
        self.assertEqual(result[0]["content_chars"], len("private document text"))
        self.assertEqual(result[0]["usage"], {"input_tokens": 3})
        self.assertEqual(result[-1]["content"], trace[-1]["content"])

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

    def test_effective_manifest_uses_external_content_hashes_and_stages_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            agent = root / "source-agent"
            (agent / "data").mkdir(parents=True)
            (agent / "data" / "manifest.json").write_text(
                '{"schema_version":1,"workflow":"test","datasource_root":"old","sources":[]}',
                encoding="utf-8",
            )
            (agent / "agent.py").write_text("VALUE = 1\n", encoding="utf-8")
            data = root / "dataset" / "documents"
            data.mkdir(parents=True)
            (data / "case.txt").write_text("confirmatory", encoding="utf-8")
            rows = [{"input": "documents/case.txt"}]

            manifest = MODULE.build_effective_manifest(agent, data, rows)
            self.assertEqual(manifest["datasource_root"], data.resolve().as_posix())
            self.assertEqual(manifest["sources"][0]["path"], "case.txt")
            self.assertEqual(len(manifest["sources"][0]["sha256"]), 64)

            staged = MODULE.stage_agent(agent, manifest, root / "staging")
            staged_manifest = json.loads(
                (staged / "data" / "manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(staged_manifest, manifest)
            self.assertEqual(
                json.loads((agent / "data" / "manifest.json").read_text(encoding="utf-8"))[
                    "datasource_root"
                ],
                "old",
            )

    def test_effective_manifest_rejects_path_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            agent = root / "agent"
            (agent / "data").mkdir(parents=True)
            (agent / "data" / "manifest.json").write_text(
                '{"schema_version":1,"sources":[]}', encoding="utf-8"
            )
            data = root / "dataset"
            data.mkdir()
            with self.assertRaisesRegex(ValueError, "unsafe datasource path"):
                MODULE.build_effective_manifest(
                    agent, data, [{"input": "documents/../secret.txt"}]
                )

    def test_resume_requires_same_contract_and_ordered_prefix(self):
        expected = {
            "agent": "agent",
            "evals": "evals.csv",
            "evals_sha256": "eval-hash",
            "datasource_root": "/dataset",
            "split": "test",
            "model": "qwen3:14b",
            "model_digest": "model-hash",
            "seed": 42,
            "invariants": {
                "system_prompt_sha256": "prompt",
                "agent_harness_sha256": "harness",
                "datasource_snapshot_sha256": "data",
                "evaluation_sha256": "eval-hash",
                "scorer_sha256": "scorer",
            },
            "sop": {"sha256": "sop"},
        }
        previous = {**expected, "cases": [{"id": "a"}]}
        self.assertEqual(MODULE.validate_resume(previous, expected, ["a", "b"]), previous["cases"])
        previous["seed"] = 7
        with self.assertRaisesRegex(ValueError, "seed"):
            MODULE.validate_resume(previous, expected, ["a", "b"])

    def test_run_payload_marks_partial_or_complete(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evals = root / "evals.csv"
            evals.write_text("id,input,output,reasoning,split\n", encoding="utf-8")
            args = argparse.Namespace(
                agent=Path("agent"),
                evals=evals,
                datasource_root=root,
                split="validation",
                model="qwen3:14b",
                seed=42,
            )
            value = MODULE.run_payload(
                args=args,
                created_at="now",
                model_digest="digest",
                system_prompt={},
                invariants={},
                sop={},
                cases=[],
                complete=False,
            )
            self.assertFalse(value["complete"])
            self.assertEqual(value["summary"]["cases"], 0)


if __name__ == "__main__":
    unittest.main()
