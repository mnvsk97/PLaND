from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/compare.py"
SPEC = importlib.util.spec_from_file_location("text_compare", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class CompareTests(unittest.TestCase):
    def test_wilson_interval_contains_observed_rate(self):
        low, high = MODULE.wilson_interval(75, 100)
        self.assertLess(low, 0.75)
        self.assertGreater(high, 0.75)

    def test_mcnemar_exact_identical_is_one(self):
        self.assertEqual(MODULE.mcnemar_exact(0, 0), 1.0)

    def test_paired_accuracy_difference(self):
        pairs = [
            ({"correct": True}, {"correct": True}),
            ({"correct": False}, {"correct": True}),
            ({"correct": True}, {"correct": False}),
        ]
        self.assertEqual(MODULE.accuracy_difference(pairs), 0.0)

    def test_token_reduction(self):
        pairs = [
            ({"total_tokens": 100}, {"total_tokens": 50}),
            ({"total_tokens": 100}, {"total_tokens": 100}),
        ]
        self.assertEqual(MODULE.token_reduction(pairs), 0.25)

    def test_mechanism_fields_are_defined_by_source(self):
        pairs = [
            ({"total_tokens": 100, "correct": True},
             {"total_tokens": 0, "correct": True, "source": "command"}),
            ({"total_tokens": 100, "correct": True},
             {"total_tokens": 80, "correct": True, "source": "model"}),
        ]
        command_pairs = [pair for pair in pairs if pair[1]["source"] == "command"]
        fallback_pairs = [pair for pair in pairs if pair[1]["source"] != "command"]
        self.assertEqual(sum(nl["total_tokens"] for nl, _ in command_pairs), 100)
        self.assertEqual(sum(h["total_tokens"] for _, h in fallback_pairs), 80)

    def test_normalizes_deepagent_summary(self):
        run = {
            "summary": {"cases": 2, "correct": 1, "accuracy": 0.5},
            "cases": [
                {"expected": "a", "actual": "a"},
                {"expected": "b", "actual": "a"},
            ],
        }
        summary = MODULE.normalized_summary(run)
        self.assertEqual(summary["model_calls"], 2)
        self.assertEqual(summary["command_calls"], 0)
        self.assertEqual(summary["macro_f1"], 1 / 3)


if __name__ == "__main__":
    unittest.main()
