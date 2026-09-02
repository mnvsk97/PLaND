import json
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "generate.py"


class GenerateTests(unittest.TestCase):
    def test_generates_one_sop_skill(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            requirements = root / "requirements.md"
            requirements.write_text("Classify the supplied document.", encoding="utf-8")
            sources = root / "sources"
            sources.mkdir()
            (sources / "buckets.txt").write_text("invoice\ncontract\n", encoding="utf-8")
            output = root / "agent"

            subprocess.run(
                [sys.executable, SCRIPT, "--workflow", "document-classifier", "--requirements", requirements, "--sources", sources, "--output", output],
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
            output = root / "agent"

            subprocess.run(
                [sys.executable, SCRIPT, "--workflow", "document-classifier", "--requirements", requirements, "--sources", sources, "--output", output, "--model-provider", "ollama"],
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
            result = subprocess.run(
                [sys.executable, SCRIPT, "--workflow", "example", "--requirements", requirements, "--sources", sources, "--output", root / "agent"],
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("contains no files", result.stderr)


if __name__ == "__main__":
    unittest.main()
