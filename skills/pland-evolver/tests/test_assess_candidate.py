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
        "evals_sha256": "eval-hash",
        "invariants": {
            "system_prompt_sha256": "prompt-hash",
            "agent_harness_sha256": "harness-hash",
            "datasource_snapshot_sha256": "data-hash",
            "evaluation_sha256": "eval-hash",
            "scorer_sha256": "scorer-hash",
        },
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
                optimization_metric="total_tokens",
                min_objective_improvement_ratio=0.0,
                require_hybrid_sop=False,
                max_validation_latency_ratio=2.0,
            )
            result = MODULE.assess(args)
            self.assertEqual(result["decision"], "reject_before_validation")
            self.assertIn("development_below_accuracy_floor", result["failed_checks"])

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
                optimization_metric="total_tokens",
                min_objective_improvement_ratio=0.0,
                require_hybrid_sop=False,
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
                optimization_metric="total_tokens",
                min_objective_improvement_ratio=0.0,
                require_hybrid_sop=False,
                max_validation_latency_ratio=2.0,
            )
            result = MODULE.assess(args)
            self.assertEqual(result["decision"], "stop_iteration_limit")
            self.assertIn("iteration_limit_exceeded", result["failed_checks"])

    def test_accuracy_is_a_floor_while_tokens_optimize(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = argparse.Namespace(
                baseline_development=self.write(root, "base.json", run_payload("development", 1.0, 200)),
                candidate_development=self.write(root, "candidate.json", run_payload("development", 0.9, 100)),
                candidate_validation=None,
                baseline_validation=None,
                candidate="candidate",
                hypothesis="reduce tokens above floor",
                iteration=1,
                max_iterations=10,
                target_accuracy=0.9,
                optimization_metric="total_tokens",
                min_objective_improvement_ratio=0.1,
                require_hybrid_sop=False,
                max_validation_latency_ratio=2.0,
            )
            result = MODULE.assess(args)
            self.assertEqual(result["decision"], "eligible_for_validation")

    def test_rejects_candidate_without_objective_improvement(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = argparse.Namespace(
                baseline_development=self.write(root, "base.json", run_payload("development", 0.9, 100)),
                candidate_development=self.write(root, "candidate.json", run_payload("development", 1.0, 120)),
                candidate_validation=None,
                baseline_validation=None,
                candidate="candidate",
                hypothesis="more expensive",
                iteration=1,
                max_iterations=10,
                target_accuracy=0.9,
                optimization_metric="total_tokens",
                min_objective_improvement_ratio=0.0,
                require_hybrid_sop=False,
                max_validation_latency_ratio=2.0,
            )
            result = MODULE.assess(args)
            self.assertEqual(result["decision"], "reject_before_validation")
            self.assertIn("development_objective_not_improved", result["failed_checks"])

    def test_rejects_changed_frozen_system_prompt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = run_payload("development", 0.9, 200)
            candidate = run_payload("development", 1.0, 100)
            candidate["invariants"]["system_prompt_sha256"] = "changed"
            args = argparse.Namespace(
                baseline_development=self.write(root, "base.json", baseline),
                candidate_development=self.write(root, "candidate.json", candidate),
                candidate_validation=None,
                baseline_validation=None,
                candidate="candidate",
                hypothesis="changed prompt",
                iteration=1,
                max_iterations=10,
                target_accuracy=0.9,
                optimization_metric="total_tokens",
                min_objective_improvement_ratio=0.0,
                require_hybrid_sop=False,
                max_validation_latency_ratio=2.0,
            )
            result = MODULE.assess(args)
            self.assertEqual(result["decision"], "reject_before_validation")
            self.assertIn("invariant_mismatch:system_prompt_sha256", result["failed_checks"])


if __name__ == "__main__":
    unittest.main()
