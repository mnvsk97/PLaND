import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts/scaffold.py"


def write_evals(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "input", "output", "reasoning"])
        writer.writeheader()
        writer.writerows(rows)


class ScaffoldTests(unittest.TestCase):
    def test_scaffold_creates_hybrid_skill(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sources = root / "sources"
            sources.mkdir()
            (sources / "rules.txt").write_text("local evidence", encoding="utf-8")
            evals = root / "evals.csv"
            write_evals(evals, [{"id": "1", "input": "x", "output": "y", "reasoning": "because"}])
            output = root / "generated"

            subprocess.run(
                [sys.executable, SCRIPT, "--task", "example-task", "--sources", sources, "--evals", evals, "--output", output],
                check=True,
            )

            skill = (output / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("references/task-evidence.md", skill)
            self.assertIn("scripts/inspect_request.py", skill)
            self.assertTrue((output / "pyproject.toml").is_file())
            inventory = json.loads((output / "INVENTORY.json").read_text(encoding="utf-8"))
            self.assertEqual(inventory["evals"]["rows"], 1)
            self.assertFalse(inventory["sources"]["copied"])

            request = root / "request.json"
            subprocess.run(
                [sys.executable, output / "scripts/inspect_request.py", "--input", "example", "--output", request],
                check=True,
            )
            result = root / "result.json"
            result.write_text('{"answer": "example"}', encoding="utf-8")
            subprocess.run(
                [sys.executable, output / "scripts/validate_result.py", "--input", result],
                check=True,
            )

    def test_scaffold_rejects_missing_eval_column(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sources = root / "sources"
            sources.mkdir()
            (sources / "rules.txt").write_text("local evidence", encoding="utf-8")
            evals = root / "evals.csv"
            evals.write_text("input,output\nx,y\n", encoding="utf-8")

            result = subprocess.run(
                [sys.executable, SCRIPT, "--task", "example-task", "--sources", sources, "--evals", evals, "--output", root / "out"],
                text=True,
                capture_output=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing required eval columns", result.stderr)


if __name__ == "__main__":
    unittest.main()
