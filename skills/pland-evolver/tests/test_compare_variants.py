import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "compare_variants.py"
SPEC = importlib.util.spec_from_file_location("compare_variants", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def run(command_steps, accuracy, tokens, latency):
    return {
        "model": "model",
        "model_digest": "digest",
        "seed": 42,
        "evals": "/evals.csv",
        "evals_sha256": "eval-hash",
        "split": "validation",
        "invariants": {
            "system_prompt_sha256": "prompt-hash",
            "agent_harness_sha256": "harness-hash",
            "datasource_snapshot_sha256": "data-hash",
            "evaluation_sha256": "eval-hash",
            "scorer_sha256": "scorer-hash",
        },
        "sop": {
            "sha256": "hash",
            "content": "SOP",
            "step_representations": {"total": 3, "english": 3 - command_steps, "reference": 0, "command": command_steps},
        },
        "summary": {
            "cases": 10,
            "correct": round(accuracy * 10),
            "accuracy": accuracy,
            "input_tokens": tokens - 10,
            "output_tokens": 10,
            "total_tokens": tokens,
            "estimated_model_cost_usd": 0.0,
            "latency_seconds": {"total": latency * 10, "mean": latency, "p95": latency * 1.2},
        },
    }


class CompareVariantsTests(unittest.TestCase):
    def test_saves_core_metric_deltas(self):
        result = MODULE.compare(run(0, 0.9, 200, 2.0), run(1, 1.0, 100, 1.5))
        delta = result["delta_hybrid_minus_natural_language"]
        self.assertAlmostEqual(delta["accuracy_points"], 0.1)
        self.assertEqual(delta["total_tokens"], -100)
        self.assertEqual(delta["total_token_ratio"], 0.5)
        self.assertEqual(delta["mean_latency_seconds"], -0.5)

    def test_rejects_non_hybrid_comparison(self):
        with self.assertRaisesRegex(ValueError, "at least one command"):
            MODULE.compare(run(0, 0.9, 200, 2.0), run(0, 1.0, 100, 1.5))

    def test_rejects_incomparable_runs(self):
        natural = run(0, 0.9, 200, 2.0)
        hybrid = run(1, 1.0, 100, 1.5)
        hybrid["seed"] = 7
        with self.assertRaisesRegex(ValueError, "seed"):
            MODULE.compare(natural, hybrid)

    def test_rejects_changed_system_prompt(self):
        natural = run(0, 0.9, 200, 2.0)
        hybrid = run(1, 1.0, 100, 1.5)
        hybrid["invariants"]["system_prompt_sha256"] = "changed"
        with self.assertRaisesRegex(ValueError, "system_prompt"):
            MODULE.compare(natural, hybrid)

    def test_accepts_evaluation_hash_aliases(self):
        natural = run(0, 0.9, 200, 2.0)
        hybrid = run(1, 1.0, 100, 1.5)
        natural["invariants"]["evals_sha256"] = natural["invariants"].pop("evaluation_sha256")
        result = MODULE.compare(natural, hybrid)
        self.assertEqual(result["delta_hybrid_minus_natural_language"]["total_tokens"], -100)

    def test_rejects_conflicting_evaluation_hash_aliases(self):
        natural = run(0, 0.9, 200, 2.0)
        hybrid = run(1, 1.0, 100, 1.5)
        hybrid["invariants"]["evals_sha256"] = "different"
        with self.assertRaisesRegex(ValueError, "evaluation_sha256"):
            MODULE.compare(natural, hybrid)


if __name__ == "__main__":
    unittest.main()
