import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/assess_baseline.py"


class AssessBaselineTests(unittest.TestCase):
    def assess(self, quality: float, attempt: int) -> str:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run = root / "run.json"
            output = root / "decision.json"
            run.write_text(json.dumps({
                "split": "development",
                "candidate_id": "baseline",
                "sop_sha256": "a" * 64,
                "summary": {"accuracy": quality, "errors": {}, "normal_completion_rate": 1.0},
            }))
            subprocess.run([
                sys.executable, SCRIPT, "--run", run, "--attempt", str(attempt),
                "--max-attempts", "10", "--minimum-quality", "0.8", "--output", output,
            ], check=True, capture_output=True, text=True)
            return json.loads(output.read_text())["decision"]

    def test_ready_at_floor(self):
        self.assertEqual(self.assess(0.8, 1), "ready_to_freeze")

    def test_refines_before_limit(self):
        self.assertEqual(self.assess(0.79, 9), "refine_baseline")

    def test_stops_at_limit(self):
        self.assertEqual(self.assess(0.79, 10), "baseline_nonviable")


if __name__ == "__main__":
    unittest.main()
