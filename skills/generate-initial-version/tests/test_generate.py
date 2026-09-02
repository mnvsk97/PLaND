import json
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "generate.py"


class GenerateTests(unittest.TestCase):
    def write_evals(self, root: Path) -> Path:
        evals = root / "evals.csv"
        evals.write_text(
            "id,input,output,reasoning,split\n"
            'case-1,invoice.txt,"{""label"":""invoice""}",gold,development\n'
            'case-2,contract.txt,"{""label"":""contract""}",gold,validation\n',
            encoding="utf-8",
        )
        return evals

    def test_generates_one_sop_skill(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            requirements = root / "requirements.md"
            requirements.write_text("Classify the supplied document.", encoding="utf-8")
            sources = root / "sources"
            sources.mkdir()
            (sources / "buckets.txt").write_text("invoice\ncontract\n", encoding="utf-8")
            evals = self.write_evals(root)
            output = root / "agent"

            subprocess.run(
                [sys.executable, SCRIPT, "--workflow", "document-classifier", "--requirements", requirements, "--sources", sources, "--evals", evals, "--output", output],
                check=True,
            )

            self.assertTrue((output / "agent.py").is_file())
            self.assertEqual(list((output / "skills").rglob("SKILL.md")), [output / "skills/document-classifier/SKILL.md"])
            agent_source = (output / "agent.py").read_text(encoding="utf-8")
            self.assertIn('skills=["/skills/"]', agent_source)
            self.assertIn("def invoke_workflow(request: str)", agent_source)
            self.assertIn("/skills/document-classifier/SKILL.md", agent_source)
            self.assertIn("FilesystemBackend", agent_source)
            compile(agent_source, str(output / "agent.py"), "exec")
            compile((output / "tools/datasources.py").read_text(encoding="utf-8"), str(output / "tools/datasources.py"), "exec")
            self.assertEqual(json.loads((output / "data/manifest.json").read_text())["workflow"], "document-classifier")
            manifest = json.loads((output / "data/manifest.json").read_text())
            self.assertEqual(manifest["evals"]["path"], str(evals.resolve()))
            profile = json.loads((output / "data/eval-profile.json").read_text())
            self.assertEqual(profile["task_kind"], "classification")
            self.assertEqual(profile["output"]["labels"], ["contract", "invoice"])
            sop = (output / "skills/document-classifier/SKILL.md").read_text()
            self.assertIn("Classify the supplied document.", sop)
            self.assertIn("`contract`, `invoice`", sop)
            self.assertNotIn("case-1", sop)
            self.assertNotIn("gold", sop)
            project = tomllib.loads((output / "pyproject.toml").read_text(encoding="utf-8"))
            self.assertEqual(project["project"]["dependencies"], ["deepagents"])
            tool_source = (output / "tools/datasources.py").read_text(encoding="utf-8")
            self.assertIn("def read_datasource(relative_path: str)", tool_source)
            self.assertEqual(json.loads((output / "data/manifest.json").read_text())["model_provider"], "generic")

    def test_generates_ollama_agent_with_declared_integration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            requirements = root / "requirements.md"
            requirements.write_text("Classify the supplied document.", encoding="utf-8")
            sources = root / "sources"
            sources.mkdir()
            (sources / "example.txt").write_text("Subject: Test", encoding="utf-8")
            evals = self.write_evals(root)
            output = root / "agent"

            subprocess.run(
                [sys.executable, SCRIPT, "--workflow", "document-classifier", "--requirements", requirements, "--sources", sources, "--evals", evals, "--output", output, "--model-provider", "ollama"],
                check=True,
            )

            agent_source = (output / "agent.py").read_text(encoding="utf-8")
            self.assertIn("from langchain_ollama import ChatOllama", agent_source)
            self.assertIn("reasoning=False", agent_source)
            self.assertIn("GeneralPurposeSubagentProfile(enabled=False)", agent_source)
            self.assertIn('"write_file"', agent_source)
            project = tomllib.loads((output / "pyproject.toml").read_text(encoding="utf-8"))
            self.assertEqual(project["project"]["dependencies"], ["deepagents", "langchain-ollama"])

    def test_rejects_empty_datasources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            requirements = root / "requirements.md"
            requirements.write_text("Do work.", encoding="utf-8")
            sources = root / "sources"
            sources.mkdir()
            evals = self.write_evals(root)
            result = subprocess.run(
                [sys.executable, SCRIPT, "--workflow", "example", "--requirements", requirements, "--sources", sources, "--evals", evals, "--output", root / "agent"],
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("contains no files", result.stderr)

    def test_rejects_invalid_eval_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            requirements = root / "requirements.md"
            requirements.write_text("Extract fields.", encoding="utf-8")
            sources = root / "sources"
            sources.mkdir()
            (sources / "sample.txt").write_text("sample", encoding="utf-8")
            evals = root / "evals.csv"
            evals.write_text("id,input\ncase-1,sample.txt\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, SCRIPT, "--workflow", "example", "--requirements", requirements,
                 "--sources", sources, "--evals", evals, "--output", root / "agent"],
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing required columns: output", result.stderr)

    def test_derives_structured_output_fields_and_types(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            requirements = root / "requirements.md"
            requirements.write_text("Extract invoice facts.", encoding="utf-8")
            sources = root / "sources"
            sources.mkdir()
            (sources / "invoice.txt").write_text("Invoice 42 Total 19.50", encoding="utf-8")
            evals = root / "evals.csv"
            evals.write_text(
                "id,input,output\n"
                'case-1,invoice.txt,"{""invoice_number"":""42"",""total"":19.5}"\n',
                encoding="utf-8",
            )
            output = root / "agent"
            subprocess.run(
                [sys.executable, SCRIPT, "--workflow", "invoice-extraction",
                 "--requirements", requirements, "--sources", sources,
                 "--evals", evals, "--output", output],
                check=True,
            )
            profile = json.loads((output / "data/eval-profile.json").read_text())
            self.assertEqual(profile["task_kind"], "structured-output")
            self.assertEqual(profile["output"]["types"], {
                "invoice_number": ["string"], "total": ["number"],
            })
            sop = (output / "skills/invoice-extraction/SKILL.md").read_text()
            self.assertIn("`invoice_number`, `total`", sop)


if __name__ == "__main__":
    unittest.main()
