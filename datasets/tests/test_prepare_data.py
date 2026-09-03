import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "prepare_data.py"
SPEC = importlib.util.spec_from_file_location("prepare_data", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class PrepareDataTests(unittest.TestCase):
    def test_spamassassin_sanitizer_removes_label_leaks_and_continuations(self):
        raw = (
            b"From: sender@example.com\r\n"
            b"X-Spam-Status: Yes, score=9\r\n"
            b" details that continue the label\r\n"
            b"Subject: [SPAM] A normal subject\r\n\r\nBody text.\r\n"
        )
        cleaned = MODULE.sanitize_email(raw)
        self.assertNotIn("X-Spam", cleaned)
        self.assertNotIn("[SPAM]", cleaned)
        self.assertNotIn("continue the label", cleaned)
        self.assertIn("Subject: A normal subject", cleaned)
        self.assertIn("Body text.", cleaned)

    def test_sroie_source_ids_include_upstream_split(self):
        fixture_rows = []
        for upstream_split in ("train", "test"):
            fixture_rows.append({
                "row_idx": 0,
                "upstream_split": upstream_split,
                "row": {
                    "image": {"src": "unused-in-unit-test"},
                    "words": ["ACME", "2026-01-01", "1 MAIN ST", "10.00"],
                    "bboxes": [[0, 0, 1, 1]] * 4,
                    "ner_tags": [0, 1, 2, 3],
                },
            })
        self.assertEqual(MODULE.sroie_source_id(fixture_rows[0]), "train:0")
        self.assertEqual(MODULE.sroie_source_id(fixture_rows[1]), "test:0")
        self.assertNotEqual(*(MODULE.sroie_source_id(row) for row in fixture_rows))

    def test_sroie_selection_preserves_official_boundaries_and_is_repeatable(self):
        train = [{"row_idx": index, "upstream_split": "train"} for index in range(8)]
        test = [{"row_idx": index, "upstream_split": "test"} for index in range(5)]
        first = MODULE.select_sroie_splits(train, test, 7, 3, 2, 5)
        second = MODULE.select_sroie_splits(list(reversed(train)), list(reversed(test)), 7, 3, 2, 5)
        self.assertEqual(first, second)
        self.assertTrue(all(item["upstream_split"] == "train" for item in first["development"] + first["validation"]))
        self.assertTrue(all(item["upstream_split"] == "test" for item in first["test"]))
        self.assertFalse({MODULE.sroie_source_id(item) for item in first["development"]} &
                         {MODULE.sroie_source_id(item) for item in first["validation"]})

    def test_balanced_selection_is_order_independent(self):
        records = [
            {"id": f"{label}-{index}", "label": label}
            for label in ("a", "b", "c") for index in range(8)
        ]
        first, labels = MODULE.choose_balanced(records, "label", "id", 18, 3, 7)
        second, _ = MODULE.choose_balanced(reversed(records), "label", "id", 18, 3, 7)
        self.assertEqual(labels, ["a", "b", "c"])
        self.assertEqual(first, second)
        self.assertEqual(dict(__import__("collections").Counter(split for split, _ in first)),
                         {"development": 12, "validation": 3, "test": 3})

    def test_case_count_must_balance_across_classes(self):
        with self.assertRaisesRegex(ValueError, "divisible"):
            MODULE.balanced_allocation(19, 3)

    def test_confirmatory_split_counts_balance_each_class(self):
        records = [
            {"id": f"{label}-{index}", "label": label}
            for label in ("a", "b") for index in range(600)
        ]
        selected, _ = MODULE.choose_balanced(
            records, "label", "id", 1200, 2, 7,
            {"development": 100, "validation": 100, "test": 1000},
        )
        counts = __import__("collections").Counter(
            (split, row["label"]) for split, row in selected
        )
        self.assertEqual(counts[("development", "a")], 50)
        self.assertEqual(counts[("validation", "b")], 50)
        self.assertEqual(counts[("test", "a")], 500)

    def test_text_deduplication_is_global_and_order_independent(self):
        records = [
            {"id": "b", "text": " Same   text ", "label": "x"},
            {"id": "a", "text": "same text", "label": "x"},
            {"id": "c", "text": "different", "label": "y"},
        ]
        first = MODULE.deduplicate_text(records, "text", "id")
        second = MODULE.deduplicate_text(reversed(records), "text", "id")
        self.assertEqual(sorted(row["id"] for row in first), ["a", "c"])
        self.assertEqual(sorted(row["id"] for row in first), sorted(row["id"] for row in second))

    def test_official_split_selection_preserves_boundaries(self):
        records = [
            {"id": f"{source}-{label}-{index}", "label": label, "upstream_split": source}
            for source in ("train", "validation", "test")
            for label in ("a", "b") for index in range(10)
        ]
        selected, _ = MODULE.choose_balanced_official_splits(
            records, "label", "id", "upstream_split",
            {"development": 4, "validation": 4, "test": 8}, 2, 7,
            {"development": "train", "validation": "validation", "test": "test"},
        )
        mapping = {"development": "train", "validation": "validation", "test": "test"}
        self.assertTrue(all(row["upstream_split"] == mapping[split] for split, row in selected))

    def test_frozen_labels_prevent_task_drift_after_exclusion(self):
        records = [
            {"id": f"{label}-{index}", "label": label}
            for label, size in (("original-a", 8), ("original-b", 8), ("new-top", 20))
            for index in range(size)
        ]
        selected, labels = MODULE.choose_balanced(
            records, "label", "id", 12, 2, 7,
            {"development": 4, "validation": 4, "test": 4},
            ["original-a", "original-b"],
        )
        self.assertEqual(labels, ["original-a", "original-b"])
        self.assertEqual({row["label"] for _, row in selected}, set(labels))

    def test_excluded_dataset_removes_ids_and_normalized_content(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); (root / "data/cases").mkdir(parents=True)
            (root / "data/cases/a.json").write_text(json.dumps({"text": "Pilot text"}))
            with (root / "evals.csv").open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=MODULE.EVAL_FIELDS); writer.writeheader()
                writer.writerow({"schema_version":"2","id":"pilot-a","benchmark":"x",
                                 "task_type":"text_classification","split":"test",
                                 "input":"data/cases/a.json","output":"{}","reasoning":"","metadata":"{}"})
            records = [{"id":"new-id","text":" pilot   TEXT ","label":"x"},
                       {"id":"safe","text":"different","label":"x"}]
            kept, manifest = MODULE.exclude_records(records, "text", "id", [root])
            self.assertEqual([row["id"] for row in kept], ["safe"])
            self.assertEqual(manifest[0]["cases"], 1)

    def test_cfpb_api_snapshot_is_read_as_canonical_rows(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "complaints-api.json"
            source.write_text(json.dumps({"hits": {"hits": [{"_source": {
                "complaint_id": "123", "product": "Credit card",
                "issue": "Incorrect fee", "complaint_what_happened": "I was charged twice.",
            }}]}}), encoding="utf-8")
            self.assertEqual(list(MODULE.iter_cfpb(source)), [{
                "Consumer complaint narrative": "I was charged twice.",
                "Product": "Credit card", "Complaint ID": "123", "Issue": "Incorrect fee",
            }])

    def test_cfpb_product_snapshot_is_read_as_canonical_rows(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "complaints-api.json"
            hit = {"_source": {"complaint_id": "321", "product": "Mortgage",
                               "issue": "Payment", "complaint_what_happened": "Payment failed."}}
            source.write_text(json.dumps({"by_product": {"Mortgage": {"hits": {"hits": [hit]}}}}))
            self.assertEqual(next(iter(MODULE.iter_cfpb(source)))["Complaint ID"], "321")


if __name__ == "__main__":
    unittest.main()
