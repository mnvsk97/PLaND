import csv
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "prepare_quality_first.py"
SPEC = importlib.util.spec_from_file_location("prepare_quality_first", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


class PrepareQualityFirstTests(unittest.TestCase):
    def test_lock_has_exact_quality_first_contract(self):
        lock = MODULE.load_lock()
        study = lock["preparations"][MODULE.PREPARATION]
        self.assertEqual(study["seed"], 20260906)
        self.assertEqual(study["exclude_prior_cases"], 1200)
        self.assertEqual(study["datasets"]["ledgar"]["splits"]["test"], 750)
        self.assertEqual(study["datasets"]["cfpb"]["splits"]["validation"], 500)
        self.assertEqual(study["datasets"]["spamassassin"]["splits"]["development"], 500)
        self.assertFalse(lock["policy"]["raw_data_tracked_in_git"])
        self.assertTrue(all(not lock["sources"][name]["redistribute_raw"]
                            for name in MODULE.DATASETS))
        self.assertEqual(
            set(lock["sources"]),
            {
                "ledgar",
                "cfpb",
                "spamassassin",
                "sroie",
                "qs_ocr_tobacco3482",
                "rvl_cdip_mirror",
            },
        )

    def test_verify_inputs_requires_hashes_counts_and_frozen_labels(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_root = root / "sources"
            confirmatory_root = root / "confirmatory"
            lock = {
                "preparations": {MODULE.PREPARATION: {
                    "exclude_prior_cases": 1,
                    "datasets": {},
                }},
                "sources": {},
            }
            for dataset in MODULE.DATASETS:
                source = source_root / dataset / ("complaints-api.json" if dataset == "cfpb" else "raw")
                source.parent.mkdir(parents=True, exist_ok=True)
                source.write_bytes(dataset.encode())
                lock["sources"][dataset] = {"files": [{
                    "path": str(source.relative_to(source_root)),
                    "bytes": source.stat().st_size,
                    "sha256": digest(dataset.encode()),
                }]}
                prior = confirmatory_root / dataset
                prior.mkdir(parents=True)
                with (prior / "evals.csv").open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.DictWriter(handle, fieldnames=["id"])
                    writer.writeheader()
                    writer.writerow({"id": "original"})
                (prior / "selection.json").write_text(
                    json.dumps({"labels": ["label"]}), encoding="utf-8"
                )
                lock["preparations"][MODULE.PREPARATION]["datasets"][dataset] = {
                    "prior_evals_sha256": MODULE.sha256(prior / "evals.csv")
                }
            resolved = MODULE.verify_inputs(lock, source_root, confirmatory_root)
            self.assertEqual(set(resolved), set(MODULE.DATASETS))

            (confirmatory_root / "ledgar/selection.json").write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "no frozen labels"):
                MODULE.verify_inputs(lock, source_root, confirmatory_root)

    def test_command_freezes_source_exclusion_labels_seed_and_splits(self):
        command = MODULE.command_for(
            "ledgar",
            Path("out/ledgar"),
            Path("sources"),
            {"prior": Path("old/ledgar"), "labels": Path("old/ledgar/selection.json")},
            {"splits": {"development": 500, "validation": 500, "test": 750}},
            20260906,
        )
        joined = " ".join(str(part) for part in command)
        self.assertIn("--source sources/ledgar", joined)
        self.assertIn("--exclude-dataset old/ledgar", joined)
        self.assertIn("--labels-from old/ledgar/selection.json", joined)
        self.assertIn("--seed 20260906", joined)
        self.assertIn("--development-cases 500", joined)
        self.assertIn("--validation-cases 500", joined)
        self.assertIn("--test-cases 750", joined)


if __name__ == "__main__":
    unittest.main()
