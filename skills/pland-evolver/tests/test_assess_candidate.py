import argparse
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "assess_candidate.py"
SPEC = importlib.util.spec_from_file_location("assess_candidate", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def run_payload(split, accuracy, tokens=100, latency=1.0, errors=None):
    return {
        "model": "model",
        "model_digest": "digest",
        "seed": 42,
        "evals": "/evals.csv",
        "split": split,
        "summary": {
            "accuracy": accuracy,
            "total_tokens": tokens,
            "errors": errors or {},
            "latency_seconds": {"mean": latency},
        },
    }


class AssessCandidateTests(unittest.TestCase):
    def write(self, root, name, payload):
        path = root / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_rejects_development_regression(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = argparse.Namespace(
                baseline_development=self.write(root, "base.json", run_payload("development", 0.9)),
                candidate_development=self.write(root, "candidate.json", run_payload("development", 0.8)),
                candidate_validation=None,
                baseline_validation=None,
                candidate="candidate",
                hypothesis="test",
                iteration=1,
                max_iterations=10,
                target_accuracy=0.9,
                max_validation_latency_ratio=2.0,
            )
            result = MODULE.assess(args)
            self.assertEqual(result["decision"], "reject_before_validation")
            self.assertIn("development_accuracy_regression", result["failed_checks"])

    def test_accepts_quality_preserving_token_reduction(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = argparse.Namespace(
                baseline_development=self.write(root, "base-dev.json", run_payload("development", 0.9, 200)),
                candidate_development=self.write(root, "candidate-dev.json", run_payload("development", 1.0, 100)),
                candidate_validation=self.write(root, "candidate-val.json", run_payload("validation", 1.0, 90, 1.2)),
                baseline_validation=self.write(root, "base-val.json", run_payload("validation", 1.0, 180, 1.0)),
                candidate="candidate",
                hypothesis="test",
                iteration=1,
                max_iterations=10,
                target_accuracy=0.9,
                max_validation_latency_ratio=2.0,
            )
            result = MODULE.assess(args)
            self.assertEqual(result["decision"], "accept")
            self.assertEqual(result["validation"]["delta"]["token_ratio"], 0.5)

    def test_stops_after_configured_iteration_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = argparse.Namespace(
                baseline_development=self.write(root, "base.json", run_payload("development", 0.9)),
                candidate_development=self.write(root, "candidate.json", run_payload("development", 1.0)),
                candidate_validation=None,
                baseline_validation=None,
                candidate="candidate-011",
                hypothesis="must not continue",
                iteration=11,
                max_iterations=10,
                target_accuracy=0.9,
                max_validation_latency_ratio=2.0,
            )
            result = MODULE.assess(args)
            self.assertEqual(result["decision"], "stop_iteration_limit")
            self.assertIn("iteration_limit_exceeded", result["failed_checks"])


if __name__ == "__main__":
    unittest.main()
