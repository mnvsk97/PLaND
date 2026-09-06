from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts/run_collection.py"
SPEC = importlib.util.spec_from_file_location("run_collection", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CollectionControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        subprocess.run(["git", "init", "-q", self.root], check=True)
        subprocess.run(["git", "-C", self.root, "config", "user.email", "test@example.com"], check=True)
        subprocess.run(["git", "-C", self.root, "config", "user.name", "Test"], check=True)
        (self.root / "protocol.md").write_text("# Frozen protocol\n")
        (self.root / "paper.md").write_text("# Paper\n")
        self.plan = self.root / "plan.json"
        self.plan.write_text(json.dumps({
            "schema_version": 1,
            "study_id": "fixture",
            "protocol": "protocol.md",
            "datasets": ["fixture"],
            "splits": {"development": 500, "selection": 1000, "final_test": 500},
            "model": {"name": "fixture", "digest": "abc"},
            "limits": {"baseline_attempts": 2, "candidate_attempts": 1},
            "acceptance": {"quality_metric": "accuracy"},
            "paper": {"source": "paper.md"},
        }) + "\n")
        subprocess.run(["git", "-C", self.root, "add", "."], check=True)
        subprocess.run(["git", "-C", self.root, "commit", "-qm", "fixture"], check=True)
        self.run_dir = self.root / "run"
        MODULE.initialize(Namespace(plan=self.plan, run_dir=self.run_dir, allow_dirty=False))

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_fixture(self, stage: str, name: str) -> Path:
        output = self.run_dir / f"{name}.txt"
        result = MODULE.run_command(Namespace(
            run_dir=self.run_dir,
            stage=stage,
            name=name,
            cwd=self.root,
            input=[],
            output=[output],
            command=["--", "python3", "-c", f"from pathlib import Path; Path({str(output)!r}).write_text('ok')"],
        ))
        self.assertEqual(result, 0)
        return output

    def test_plan_change_is_rejected(self) -> None:
        self.plan.write_text(self.plan.read_text() + " ")
        with self.assertRaisesRegex(ValueError, "frozen plan changed"):
            MODULE.load_state(self.run_dir)

    def test_safety_hold_blocks_new_and_resumed_commands(self) -> None:
        self.run_fixture("prepare", "prepare")
        (self.run_dir / "collection-hold.json").write_text('{"reason":"invalid data"}')
        for name in ["prepare", "another"]:
            with self.assertRaisesRegex(ValueError, "collection safety hold"):
                self.run_fixture("prepare", name)
        with self.assertRaisesRegex(ValueError, "collection safety hold"):
            MODULE.complete_stage(Namespace(run_dir=self.run_dir, stage="prepare"))

    def test_one_candidate_attempt_allows_generation_run_and_assessment(self) -> None:
        self.run_fixture("prepare", "prepare")
        MODULE.complete_stage(Namespace(run_dir=self.run_dir, stage="prepare"))
        baseline = self.run_fixture("baseline-development", "baseline")
        MODULE.decision(Namespace(run_dir=self.run_dir, stage="baseline-development", value="ready", evidence=baseline))
        self.run_fixture("candidate-development", "generate-candidate")
        self.run_fixture("candidate-development", "measure-candidate")
        assessment = self.run_fixture("candidate-development", "assess-candidate")
        MODULE.decision(Namespace(run_dir=self.run_dir, stage="candidate-development", value="reject", evidence=assessment))
        with self.assertRaisesRegex(ValueError, "terminal or frozen"):
            self.run_fixture("candidate-development", "second-candidate")

    def test_wrong_paper_split_is_rejected(self) -> None:
        plan = json.loads(self.plan.read_text())
        plan["splits"] = {"development": 100, "selection": 100, "final_test": 1000}
        wrong = self.root / "wrong-plan.json"
        wrong.write_text(json.dumps(plan) + "\n")
        with self.assertRaisesRegex(ValueError, "requires exactly 500 development"):
            MODULE.validate_plan(plan, wrong, self.root)

    def test_final_test_is_gated_and_completed_commands_resume(self) -> None:
        with self.assertRaisesRegex(ValueError, "selection must be accepted"):
            self.run_fixture("final-test", "too-early")

        prepared = self.run_fixture("prepare", "prepare")
        MODULE.complete_stage(Namespace(run_dir=self.run_dir, stage="prepare"))

        baseline = self.run_fixture("baseline-development", "baseline-1")
        MODULE.decision(Namespace(run_dir=self.run_dir, stage="baseline-development", value="ready", evidence=baseline))

        candidate = self.run_fixture("candidate-development", "candidate-1")
        MODULE.decision(Namespace(run_dir=self.run_dir, stage="candidate-development", value="ready", evidence=candidate))

        selection = self.run_fixture("selection", "selection")
        MODULE.decision(Namespace(run_dir=self.run_dir, stage="selection", value="accept", evidence=selection))
        final = self.run_fixture("final-test", "final")
        MODULE.complete_stage(Namespace(run_dir=self.run_dir, stage="final-test"))

        state, ledger = MODULE.load_state(self.run_dir)
        self.assertEqual(state["stages"]["final-test"], "complete")
        before = len(ledger["events"])
        self.assertEqual(MODULE.run_command(Namespace(
            run_dir=self.run_dir,
            stage="final-test",
            name="final",
            cwd=self.root,
            input=[],
            output=[final],
            command=["--", "false"],
        )), 0)
        _, ledger = MODULE.load_state(self.run_dir)
        self.assertEqual(len(ledger["events"]), before)
        self.assertTrue(prepared.exists())

        packaged = self.run_fixture("package-evidence", "package")
        MODULE.complete_stage(Namespace(run_dir=self.run_dir, stage="package-evidence"))
        MODULE.create_manifest(Namespace(run_dir=self.run_dir))
        manifest = json.loads((self.run_dir / "evidence-manifest.json").read_text())
        self.assertEqual(manifest["study_id"], "fixture")
        manifested_paths = {item["path"] for item in manifest["artifacts"]}
        self.assertIn(str(packaged.resolve()), manifested_paths)

    def test_failure_is_preserved(self) -> None:
        result = MODULE.run_command(Namespace(
            run_dir=self.run_dir,
            stage="prepare",
            name="failed-preflight",
            cwd=self.root,
            input=[],
            output=[],
            command=["--", "python3", "-c", "raise SystemExit(7)"],
        ))
        self.assertEqual(result, 1)
        _, ledger = MODULE.load_state(self.run_dir)
        self.assertEqual(ledger["events"][0]["status"], "failed")
        self.assertEqual(ledger["events"][0]["exit_code"], 7)


if __name__ == "__main__":
    unittest.main()
