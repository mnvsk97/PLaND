import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "assess_results.py"
SPEC = importlib.util.spec_from_file_location("assess_results", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class AssessmentTests(unittest.TestCase):
    def test_rejects_nonviable_baseline(self):
        result = MODULE.decision({"field_f1": 0.0, "total_tokens": 100},
                                 {"field_f1": 0.0, "total_tokens": 50}, 0.5)
        self.assertFalse(result["accepted"])
        self.assertFalse(result["baseline_viable"])

    def test_accepts_only_quality_preserving_improvement(self):
        result = MODULE.decision({"field_f1": 0.8, "total_tokens": 100},
                                 {"field_f1": 0.8, "total_tokens": 90}, 0.5)
        self.assertTrue(result["accepted"])


if __name__ == "__main__":
    unittest.main()
