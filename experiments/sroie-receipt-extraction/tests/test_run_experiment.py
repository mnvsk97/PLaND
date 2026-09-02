import importlib.util
import csv
import json
import tempfile
import unittest
from unittest import mock
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_experiment.py"
SPEC = importlib.util.spec_from_file_location("run_experiment", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class ExperimentTests(unittest.TestCase):
    def test_field_f1(self):
        expected = {"company": "ACME SDN BHD", "date": "01/02/2026", "address": "1 Main St", "total": "RM 10.00"}
        self.assertEqual(MODULE.field_f1(expected, expected), 1.0)

    def test_word_error_rate(self):
        self.assertEqual(MODULE.word_error_rate(["one", "two"], ["one", "two"]), 0.0)
        self.assertEqual(MODULE.word_error_rate(["one", "two"], ["one"]), 0.5)

    def test_sop_representations(self):
        baseline = MODULE.sop_snapshot(MODULE.ROOT / "nl-baseline/SKILL.md")
        hybrid = MODULE.sop_snapshot(MODULE.ROOT / "hybrid/SKILL.md")
        self.assertEqual(baseline["variant"], "natural_language")
        self.assertEqual(hybrid["variant"], "hybrid")

    def test_ocr_words_rejects_unknown_backend(self):
        with self.assertRaisesRegex(ValueError, "unsupported OCR backend"):
            MODULE.ocr_words(Path("receipt.jpg"), {"backend": "unknown"})

    def test_select_rows_can_take_one_complete_split(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with (root / "evals.csv").open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["id", "split"])
                writer.writeheader()
                writer.writerows([
                    {"id": "v2", "split": "validation"},
                    {"id": "d1", "split": "development"},
                    {"id": "v1", "split": "validation"},
                ])
            rows = MODULE.select_rows(root, cases=20, split="validation", limit=2)
            self.assertEqual([row["id"] for row in rows], ["v1", "v2"])

    @mock.patch.object(MODULE.subprocess, "run")
    def test_liteparse_words_uses_structured_text_items(self, run):
        def fake_run(command, **kwargs):
            output = Path(command[command.index("--output") + 1])
            output.write_text(json.dumps({"pages": [{"text_items": [
                {"text": "OJC MARKETING"}, {"text": "170.00"}
            ]}]}))
            return mock.Mock(stderr="", stdout="")

        run.side_effect = fake_run
        words, elapsed, stderr = MODULE.liteparse_words(Path("receipt.jpg"), {
            "backend": "liteparse", "language": "eng", "dpi": 300, "workers": 2
        })
        self.assertEqual(words, ["OJC", "MARKETING", "170.00"])
        self.assertGreaterEqual(elapsed, 0)
        self.assertEqual(stderr, "")
        command = run.call_args.args[0]
        self.assertIn("--ocr-language", command)
        self.assertIn("--num-workers", command)


if __name__ == "__main__":
    unittest.main()
