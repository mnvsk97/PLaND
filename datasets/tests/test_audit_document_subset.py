import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/audit_document_subset.py"
SPEC = importlib.util.spec_from_file_location("audit_document_subset", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DocumentSubsetAuditTests(unittest.TestCase):
    def _fixture(self, root: Path) -> None:
        (root / "documents").mkdir(parents=True)
        rows = []
        records = []
        for split, source_split in (("development", "train"), ("validation", "validation"), ("test", "test")):
            identifier = f"{split}-1"
            relative = f"documents/{identifier}.txt"
            source = root / "sources" / f"{identifier}.txt"
            source.parent.mkdir(exist_ok=True)
            payload = f"document payload for {identifier}\n"
            (root / relative).write_text(payload, encoding="utf-8")
            source.write_text(payload, encoding="utf-8")
            rows.append({"id": identifier, "split": split, "input": relative, "output": "label"})
            records.append({
                "id": identifier,
                "experiment_split": split,
                "source_split": source_split,
                "source": str(source),
                "source_sha256": MODULE.digest(source),
            })
        with (root / "evals.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        (root / "selection.json").write_text(json.dumps({"dataset": "fixture", "records": records}), encoding="utf-8")

    def test_missing_declared_source_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._fixture(root)
            selection = json.loads((root / "selection.json").read_text())
            Path(selection["records"][0]["source"]).unlink()
            proof = MODULE.audit(root)
            self.assertEqual(proof["checks"]["source_hash_errors"], 1)
            self.assertFalse(proof["passed"])

    def test_source_hash_cannot_be_rebound_to_another_row(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._fixture(root)
            selection_path = root / "selection.json"
            selection = json.loads(selection_path.read_text())
            selection["records"][0]["source_sha256"] = selection["records"][1]["source_sha256"]
            selection_path.write_text(json.dumps(selection))
            proof = MODULE.audit(root)
            self.assertGreater(proof["checks"]["source_hash_errors"], 0)
            self.assertFalse(proof["passed"])

    def test_repeat_with_changed_input_bytes_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            current, repeat = base / "current", base / "repeat"
            self._fixture(current)
            self._fixture(repeat)
            (repeat / "documents/development-1.txt").write_text("changed\n", encoding="utf-8")
            proof = MODULE.audit(current, repeat=repeat)
            self.assertFalse(proof["checks"]["repeatability"]["input_manifest"])
            self.assertFalse(proof["passed"])


if __name__ == "__main__":
    unittest.main()
