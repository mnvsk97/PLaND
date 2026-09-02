from __future__ import annotations

import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("tau_runner", ROOT / "run_experiment.py")
RUNNER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(RUNNER)


class RunnerTests(unittest.TestCase):
    def test_subset_rule_is_split_bounded_and_ordered(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evals.csv"
            with path.open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["split", "metadata"])
                writer.writeheader()
                for split, identifier in [("development", "d1"), ("validation", "v1"), ("development", "d2"), ("test", "t1")]:
                    writer.writerow({"split": split, "metadata": json.dumps({"upstream_task_id": identifier})})
            self.assertEqual(
                RUNNER.subset_ids(path, {"development": 2, "validation": 1, "test": 1}),
                ["d1", "v1", "d2", "t1"],
            )

    def test_representation_distinguishes_nl_and_hybrid(self):
        nl = RUNNER.sop_stats(ROOT / "sop/nl/SKILL.md")
        hybrid = RUNNER.sop_stats(ROOT / "sop/hybrid/SKILL.md")
        self.assertEqual(nl["command_steps"], 0)
        self.assertGreaterEqual(hybrid["command_steps"], 1)
        self.assertGreaterEqual(hybrid["reference_steps"], 1)


if __name__ == "__main__":
    unittest.main()
