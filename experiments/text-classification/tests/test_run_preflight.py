import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/run_experiment.py"
BASELINE = """# SOP

1. [S01] Read the complete item. <!-- pland:english -->
2. [S02] Classify the item using the supplied labels. <!-- pland:english -->
3. [S03] Return the required JSON. <!-- pland:english -->
"""


class RunPreflightTests(unittest.TestCase):
    def fixture(self, root: Path, fallback: str):
        dataset = root / "dataset"
        (dataset / "data").mkdir(parents=True)
        (dataset / "data/case.json").write_text(json.dumps({"text": "example"}))
        with (dataset / "evals.csv").open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["id", "split", "input", "output"])
            writer.writeheader(); writer.writerow({
                "id": "one", "split": "development", "input": "data/case.json",
                "output": json.dumps({"label": "a"}),
            })
        (dataset / "selection.json").write_text("{}\n")
        baseline = root / "baseline.md"; baseline.write_text(BASELINE)
        candidate = root / "candidate.md"
        candidate.write_text(f"""# SOP

1. [S01] Read the complete item. <!-- pland:english -->
2. [S02] Run `python classify.py`. <!-- pland:command fallback=S02 -->
   Fallback [S02]: {fallback} <!-- pland:fallback -->
3. [S03] Return the required JSON. <!-- pland:english -->
""")
        classifier = root / "classify.py"
        classifier.write_text("def classify(text, labels):\n    return {'label': labels[0], 'matched_rule': 'fixture'}\n")
        system = root / "system.md"; system.write_text("Classify.")
        return dataset, baseline, candidate, classifier, system

    def command(self, root: Path, fallback: str):
        dataset, baseline, candidate, classifier, system = self.fixture(root, fallback)
        return [
            sys.executable, SCRIPT, "--dataset", dataset, "--split", "development",
            "--system-prompt", system, "--sop", candidate, "--classifier", classifier,
            "--baseline-sop", baseline, "--command-step-id", "S02",
            "--output", root / "preflight.json", "--preflight-only",
        ]

    def test_hybrid_preflight_freezes_exact_link_without_model(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(self.command(root, "Classify the item using the supplied labels."),
                           check=True, capture_output=True, text=True)
            result = json.loads((root / "preflight.json").read_text())
            self.assertFalse(result["model_invoked"])
            self.assertEqual(result["sop_contract"]["command_fallback_links"][0]["command_step_id"], "S02")
            self.assertEqual(result["candidate_id"], "hybrid")
            self.assertEqual(len(result["skill_content_sha256"]), 64)
            self.assertEqual(len(result["frozen_manifest_sha256"]), 64)
            self.assertEqual(
                len(result["invariants"]["datasource_snapshot_sha256"]), 64
            )

    def test_hybrid_preflight_rejects_rewritten_fallback(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = subprocess.run(self.command(Path(temporary), "Classify it."),
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("not the exact baseline instruction", result.stderr)


if __name__ == "__main__":
    unittest.main()
