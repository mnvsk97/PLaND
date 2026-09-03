import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILLS = Path(__file__).resolve().parents[2]
GENERATOR = SKILLS / "generate-initial-version" / "scripts" / "generate.py"
ASSESSOR = Path(__file__).resolve().parents[1] / "scripts" / "assess_candidate.py"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SkillPipelineTests(unittest.TestCase):
    def test_generated_scaffold_flows_into_paired_evolver_assessment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            requirements = root / "requirements.md"
            requirements.write_text(
                "Route each support message into its known service queue.", encoding="utf-8"
            )
            sources = root / "sources"
            sources.mkdir()
            (sources / "queues.txt").write_text("billing\ntechnical\n", encoding="utf-8")
            evals = root / "evals.csv"
            evals.write_text(
                "id,input,output,reasoning,split\n"
                'private-case-a,a.txt,"{""label"":""billing""}",private rationale,development\n'
                'private-case-b,b.txt,"{""label"":""technical""}",private rationale,validation\n',
                encoding="utf-8",
            )
            agent = root / "agent"
            subprocess.run(
                [
                    sys.executable,
                    GENERATOR,
                    "--workflow",
                    "support-routing",
                    "--requirements",
                    requirements,
                    "--sources",
                    sources,
                    "--evals",
                    evals,
                    "--output",
                    agent,
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            manifest = json.loads((agent / "data/manifest.json").read_text())
            profile = json.loads((agent / "data/eval-profile.json").read_text())
            sop_text = (agent / "skills/support-routing/SKILL.md").read_text()
            self.assertEqual(manifest["evals"]["sha256"], digest(evals))
            self.assertEqual(profile["task_kind"], "classification")
            self.assertEqual(profile["output"]["labels"], ["billing", "technical"])
            self.assertIn("known service queue", sop_text)
            self.assertNotIn("private-case-a", json.dumps(profile) + sop_text)
            self.assertNotIn("private rationale", json.dumps(profile) + sop_text)

            candidate_sop = root / "candidate-SKILL.md"
            candidate_sop_text = sop_text.replace(
                "2. [S02] Use the approved datasource tools to read only the relevant evidence; "
                "the source collection contains .txt files. <!-- pland:english -->",
                "2. [S02] Run `python scripts/route.py` for stable routing and use its result when "
                "it returns a known bucket. <!-- pland:command -->",
            )
            self.assertNotEqual(candidate_sop_text, sop_text)
            candidate_sop.write_text(candidate_sop_text, encoding="utf-8")

            shared = {
                "model": "fixture-model",
                "model_digest": "fixture-model-digest",
                "seed": 42,
                "evals": str(evals),
                "evals_sha256": digest(evals),
            }
            frozen = {
                "system_prompt_sha256": digest(agent / "instructions.md"),
                "agent_harness_sha256": digest(agent / "agent.py"),
                "datasource_snapshot_sha256": manifest["sources"][0]["sha256"],
                "scorer_sha256": "fixture-scorer",
            }

            def run(split: str, tokens: int, *, candidate: bool) -> dict:
                invariants = dict(frozen)
                # Exercise both supported names across a single comparison.
                invariants["evaluation_sha256" if candidate else "evals_sha256"] = digest(evals)
                return {
                    **shared,
                    "experiment_id": "pipeline-fixture",
                    "run_id": f"{'candidate' if candidate else 'baseline'}-{split}",
                    "candidate_id": "candidate-001" if candidate else "baseline",
                    "attempt": 1 if candidate else 0,
                    "sop_sha256": digest(candidate_sop) if candidate else digest(agent / "skills/support-routing/SKILL.md"),
                    "skill_content_sha256": "a" * 64 if candidate else "b" * 64,
                    "frozen_manifest_sha256": "c" * 64,
                    "split": split,
                    "invariants": invariants,
                    "sop": {
                        "variant": "hybrid" if candidate else "natural_language",
                        "sha256": digest(candidate_sop) if candidate else digest(
                            agent / "skills/support-routing/SKILL.md"
                        ),
                        "content": candidate_sop_text if candidate else sop_text,
                        "step_representations": {
                            "total": 4,
                            "english": 3 if candidate else 4,
                            "reference": 0,
                            "command": 1 if candidate else 0,
                        },
                    },
                    "summary": {
                        "accuracy": 1.0,
                        "total_tokens": tokens,
                        "errors": {},
                        "latency_seconds": {"mean": 1.0},
                    },
                }

            paths = {}
            for name, payload in {
                "baseline-development": run("development", 200, candidate=False),
                "candidate-development": run("development", 100, candidate=True),
                "baseline-validation": run("validation", 180, candidate=False),
                "candidate-validation": run("validation", 90, candidate=True),
            }.items():
                paths[name] = root / f"{name}.json"
                paths[name].write_text(json.dumps(payload), encoding="utf-8")

            assessment = root / "assessment.json"
            subprocess.run(
                [
                    sys.executable,
                    ASSESSOR,
                    "--baseline-development",
                    paths["baseline-development"],
                    "--candidate-development",
                    paths["candidate-development"],
                    "--baseline-validation",
                    paths["baseline-validation"],
                    "--candidate-validation",
                    paths["candidate-validation"],
                    "--candidate",
                    "candidate-001",
                    "--hypothesis",
                    "replace one stable routing step",
                    "--target-accuracy",
                    "0.9",
                    "--require-hybrid-sop",
                    "--output",
                    assessment,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            result = json.loads(assessment.read_text())
            self.assertEqual(result["decision"], "accept")
            self.assertEqual(result["failed_checks"], [])
            self.assertEqual(result["validation"]["delta"]["tokens"], -90)


if __name__ == "__main__":
    unittest.main()
