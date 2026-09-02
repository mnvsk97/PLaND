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

    def test_tau_fixture_emits_canonical_schema_without_leaking_evals(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            tasks = []
            for index in range(10):
                tasks.append({
                    "id": str(index), "user_scenario": {"request": f"request {index}"},
                    "initial_state": None,
                    "evaluation_criteria": {"actions": [{"name": "lookup"}], "reward_basis": ["DB"]},
                })
            source = base / "tasks.json"
            source.write_text(json.dumps(tasks), encoding="utf-8")
            policy = base / "policy.md"
            policy.write_text("Public retail policy.\n", encoding="utf-8")
            output = base / "prepared"
            args = SimpleNamespace(source=source, policy_source=policy, cases=10, seed=17)
            output.mkdir()
            MODULE.prepare_tau(args, output)
            with (output / "evals.csv").open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(list(rows[0]), MODULE.EVAL_FIELDS)
            self.assertEqual(len(rows), 10)
            case = json.loads((output / rows[0]["input"]).read_text(encoding="utf-8"))
            self.assertNotIn("evaluation_criteria", case)
            self.assertIn("actions", json.loads(rows[0]["output"]))
            self.assertEqual(json.loads((output / "dataset-summary.json").read_text())["by_split"],
                             {"development": 6, "validation": 2, "test": 2})

    def test_case_count_must_balance_across_classes(self):
        with self.assertRaisesRegex(ValueError, "divisible"):
            MODULE.balanced_allocation(19, 3)

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


if __name__ == "__main__":
    unittest.main()
