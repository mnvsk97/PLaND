import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "aggregate.py"
SPEC = importlib.util.spec_from_file_location("variance_aggregate", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class AggregateTests(unittest.TestCase):
    def test_distribution_uses_sample_sd_and_range(self):
        result = MODULE.distribution([0.8, 0.9, 1.0])
        self.assertAlmostEqual(result["mean"], 0.9)
        self.assertAlmostEqual(result["sample_sd"], 0.1)
        self.assertAlmostEqual(result["range"], 0.2)

    def test_stability_reports_pairwise_and_any_disagreement(self):
        runs = [
            {"seed": 1, "cases": [{"id": "a", "actual": "x"}, {"id": "b", "actual": "x"}]},
            {"seed": 2, "cases": [{"id": "a", "actual": "x"}, {"id": "b", "actual": "y"}]},
            {"seed": 3, "cases": [{"id": "a", "actual": "x"}, {"id": "b", "actual": "y"}]},
        ]
        result = MODULE.stability(runs, ["a", "b"])
        self.assertEqual(result["any_disagreement_cases"], 1)
        self.assertEqual([item["disagreement_cases"] for item in result["pairwise"]], [1, 1, 0])

    def test_quantiles(self):
        result = MODULE.quantiles([1, 2, 3, 4, 5])
        self.assertEqual(result["median"], 3)
        self.assertEqual(result["p95"], 4.8)


if __name__ == "__main__":
    unittest.main()
