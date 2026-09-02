import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/audit_sroie.py"
SPEC = importlib.util.spec_from_file_location("audit_sroie", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SroieAuditTests(unittest.TestCase):
    def _fixture(self, root: Path, shared_image: bytes | None = None) -> Path:
        (root / "cases").mkdir(parents=True)
        (root / "images").mkdir()
        rows = []
        selected = []
        for index, split in enumerate(("development", "validation", "test")):
            identifier = f"{split}-{index}"
            image_rel = f"images/{identifier}.jpg"
            image = root / image_rel
            image.write_bytes(shared_image if shared_image is not None and index == 0 else f"image-{identifier}".encode())
            case_rel = f"cases/{identifier}.json"
            (root / case_rel).write_text(json.dumps({"image": image_rel, "frozen_ocr": [identifier]}))
            output = json.dumps({"company": "x", "date": "y", "address": "z", "total": "1"})
            metadata = json.dumps({"image_sha256": MODULE.digest(image), "source_split": "test" if split == "test" else "train"})
            rows.append({"id": identifier, "split": split, "input": case_rel, "output": output, "metadata": metadata})
            selected.append({"id": identifier, "split": split})
        with (root / "evals.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
            writer.writeheader(); writer.writerows(rows)
        source = root / "source.json"
        source.write_text("[]\n")
        selection = {
            "dataset": "fixture", "selected": selected, "prior_pilot_ids": [],
            "official_source_counts": {"train": 2, "test": 1}, "seed": 1,
            "selection_rule": "fixture", "requested_counts": {"development": 1, "validation": 1, "test": 1},
            "sources": [{"path": "source.json", "sha256": MODULE.digest(source), "bytes": source.stat().st_size}],
        }
        (root / "selection.json").write_text(json.dumps(selection))
        (root / "dataset-summary.json").write_text("{}\n")
        return source

    def test_source_snapshot_must_match_declared_hash(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self._fixture(root)
            source.write_text("changed\n")
            proof = MODULE.audit(root, source_snapshot=source)
            self.assertFalse(proof["checks"]["source_snapshot_verified"])
            self.assertFalse(proof["passed"])

    def test_pilot_image_overlap_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            current, pilot = base / "current", base / "pilot"
            shared = b"same-image"
            source = self._fixture(current, shared_image=shared)
            self._fixture(pilot, shared_image=shared)
            proof = MODULE.audit(current, pilot=pilot, source_snapshot=source)
            self.assertGreater(proof["checks"]["pilot_image_overlap_count"], 0)
            self.assertFalse(proof["passed"])


if __name__ == "__main__":
    unittest.main()
