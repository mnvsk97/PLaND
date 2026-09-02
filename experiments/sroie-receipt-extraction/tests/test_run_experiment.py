import importlib.util
import unittest
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


if __name__ == "__main__":
    unittest.main()
