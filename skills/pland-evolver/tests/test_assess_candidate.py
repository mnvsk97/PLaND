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


def run_payload(split, accuracy, tokens=100, latency=1.0, errors=None, candidate_id="baseline"):
    digest = "a" * 64
    return {
        "experiment_id": "experiment",
        "run_id": f"run-{split}",
        "candidate_id": candidate_id,
        "attempt": 0,
        "model": "model",
        "model_digest": "digest",
        "seed": 42,
        "evals": "/evals.csv",
        "evals_sha256": digest,
        "sop_sha256": digest,
        "skill_content_sha256": digest,
        "frozen_manifest_sha256": digest,
        "invariants": {
            "system_prompt_sha256": "prompt-hash",
            "agent_harness_sha256": "harness-hash",
            "datasource_snapshot_sha256": "data-hash",
            "evaluation_sha256": digest,
            "scorer_sha256": "scorer-hash",
        },
        "split": split,
        "summary": {
            "accuracy": accuracy,
            "total_tokens": tokens,
            "errors": errors or {},
            "latency_seconds": {"mean": latency},
            "normal_completion_rate": 1.0,
        },
    }


class AssessCandidateTests(unittest.TestCase):
    def write(self, root, name, payload):
        path = root / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_skill_content_hash_tracks_references_and_scripts_not_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "references").mkdir()
            (root / "scripts").mkdir()
            (root / "assets").mkdir()
            (root / "SKILL.md").write_text("SOP", encoding="utf-8")
            (root / "references/rules.md").write_text("rules", encoding="utf-8")
            (root / "scripts/run.py").write_text("print('ok')", encoding="utf-8")
            (root / "assets/logo.txt").write_text("one", encoding="utf-8")
            paths = ["SKILL.md", "references/rules.md", "scripts/run.py"]
            before = MODULE.skill_content_evidence(root, paths)
            (root / "assets/logo.txt").write_text("two", encoding="utf-8")
            self.assertEqual(before, MODULE.skill_content_evidence(root, paths))
            (root / "scripts/run.py").write_text("print('changed')", encoding="utf-8")
            after = MODULE.skill_content_evidence(root, paths)
            self.assertNotEqual(before["sha256"], after["sha256"])
            self.assertEqual(len(after["sha256"]), 64)

    def test_rejects_development_regression(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = argparse.Namespace(
                baseline_development=self.write(root, "base.json", run_payload("development", 0.9)),
                candidate_development=self.write(root, "candidate.json", run_payload("development", 0.8, candidate_id="candidate")),
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
            self.assertIn("development_below_quality_floor", result["failed_checks"])

    def test_accepts_generic_workflow_quality_without_accuracy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = run_payload("development", 0.9, 200)
            candidate = run_payload("development", 0.95, 100, candidate_id="candidate")
            for payload, value in ((baseline, 0.9), (candidate, 0.95)):
                payload["quality_metric"] = "task_success"
                payload["summary"]["quality"] = value
                del payload["summary"]["accuracy"]
            args = argparse.Namespace(
                baseline_development=self.write(root, "base.json", baseline),
                candidate_development=self.write(root, "candidate.json", candidate),
                candidate_validation=None, baseline_validation=None,
                candidate="candidate", hypothesis="workflow quality",
                iteration=1, max_iterations=10, target_quality=0.8,
                minimum_baseline_quality=0.8, non_inferiority_margin=None,
                optimization_metric="total_tokens", min_objective_improvement_ratio=0.0,
                require_hybrid_sop=False, max_validation_latency_ratio=2.0,
            )
            result = MODULE.assess(args)
            self.assertEqual(result["decision"], "eligible_for_validation")
            self.assertEqual(result["quality_metric"], "task_success")
            self.assertAlmostEqual(result["development"]["delta"]["quality"], 0.05)

    def test_stops_when_baseline_is_nonviable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = argparse.Namespace(
                baseline_development=self.write(root, "base.json", run_payload("development", 0.0)),
                candidate_development=self.write(root, "candidate.json", run_payload("development", 0.5, candidate_id="candidate")),
                candidate_validation=None, baseline_validation=None,
                candidate="candidate", hypothesis="must establish feasibility first",
                iteration=1, max_iterations=10, target_accuracy=0.8,
                minimum_baseline_quality=0.1, non_inferiority_margin=None,
                optimization_metric="total_tokens", min_objective_improvement_ratio=0.0,
                require_hybrid_sop=False, max_validation_latency_ratio=2.0,
            )
            result = MODULE.assess(args)
            self.assertEqual(result["decision"], "baseline_nonviable")

    def test_applies_non_inferiority_margin(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = argparse.Namespace(
                baseline_development=self.write(root, "base-dev.json", run_payload("development", 0.9, 200)),
                candidate_development=self.write(root, "candidate-dev.json", run_payload("development", 0.9, 100, candidate_id="candidate")),
                baseline_validation=self.write(root, "base-val.json", run_payload("validation", 0.95, 200)),
                candidate_validation=self.write(root, "candidate-val.json", run_payload("validation", 0.85, 100, candidate_id="candidate")),
                candidate="candidate", hypothesis="quality loss too large",
                iteration=1, max_iterations=10, target_accuracy=0.8,
                minimum_baseline_quality=0.8, non_inferiority_margin=0.02,
                optimization_metric="total_tokens", min_objective_improvement_ratio=0.0,
                require_hybrid_sop=False, max_validation_latency_ratio=2.0,
            )
            result = MODULE.assess(args)
            self.assertEqual(result["decision"], "reject_after_validation")
            self.assertIn("validation_non_inferiority_failure", result["failed_checks"])

    def test_accepts_quality_preserving_token_reduction(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = argparse.Namespace(
                baseline_development=self.write(root, "base-dev.json", run_payload("development", 0.9, 200)),
                candidate_development=self.write(root, "candidate-dev.json", run_payload("development", 1.0, 100, candidate_id="candidate")),
                candidate_validation=self.write(root, "candidate-val.json", run_payload("validation", 1.0, 90, 1.2, candidate_id="candidate")),
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
                candidate_development=self.write(root, "candidate.json", run_payload("development", 1.0, candidate_id="candidate-011")),
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
                candidate_development=self.write(root, "candidate.json", run_payload("development", 0.9, 100, candidate_id="candidate")),
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
                candidate_development=self.write(root, "candidate.json", run_payload("development", 1.0, 120, candidate_id="candidate")),
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

    def test_rejects_equal_expense_when_minimum_is_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = argparse.Namespace(
                baseline_development=self.write(root, "base.json", run_payload("development", 0.9, 100)),
                candidate_development=self.write(root, "candidate.json", run_payload("development", 1.0, 100, candidate_id="candidate")),
                candidate_validation=None,
                baseline_validation=None,
                candidate="candidate",
                hypothesis="equal expense is not improvement",
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

    def test_rejects_final_acceptance_without_baseline_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = argparse.Namespace(
                baseline_development=self.write(root, "base-dev.json", run_payload("development", 0.9, 200)),
                candidate_development=self.write(root, "candidate-dev.json", run_payload("development", 1.0, 100, candidate_id="candidate")),
                candidate_validation=self.write(root, "candidate-val.json", run_payload("validation", 1.0, 90, candidate_id="candidate")),
                baseline_validation=None,
                candidate="candidate",
                hypothesis="validation must be paired",
                iteration=1,
                max_iterations=10,
                target_accuracy=0.9,
                optimization_metric="total_tokens",
                min_objective_improvement_ratio=0.0,
                require_hybrid_sop=False,
                max_validation_latency_ratio=2.0,
            )
            result = MODULE.assess(args)
            self.assertEqual(result["decision"], "reject_after_validation")
            self.assertIn("missing_baseline_validation", result["failed_checks"])

    def test_accepts_evals_sha256_invariant_alias(self):
        baseline = run_payload("development", 0.9, 200)
        candidate = run_payload("development", 1.0, 100, candidate_id="candidate")
        baseline["invariants"]["evals_sha256"] = baseline["invariants"].pop("evaluation_sha256")
        candidate["invariants"]["evals_sha256"] = candidate["invariants"].pop("evaluation_sha256")
        self.assertNotIn("invariant_mismatch:evaluation_sha256", MODULE.comparable(baseline, candidate))

    def test_rejects_changed_runtime_settings(self):
        baseline = run_payload("development", 0.9, 200)
        candidate = run_payload("development", 1.0, 100, candidate_id="candidate")
        baseline["runtime"] = {"num_ctx": 4096, "workers": 2}
        candidate["runtime"] = {"num_ctx": 8192, "workers": 2}
        self.assertIn("invariant_mismatch:runtime", MODULE.comparable(baseline, candidate))

    def test_rejects_changed_frozen_system_prompt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = run_payload("development", 0.9, 200)
            candidate = run_payload("development", 1.0, 100, candidate_id="candidate")
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
