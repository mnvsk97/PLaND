import csv, importlib.util, json, tempfile, unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/audit_prepared.py"
SPEC = importlib.util.spec_from_file_location("audit_prepared", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(MODULE)

class AuditTests(unittest.TestCase):
    def test_clean_balanced_fixture_passes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); (root/"data/cases").mkdir(parents=True)
            rows=[]
            for split in ("development","validation","test"):
                for label in ("a","b"):
                    identifier=f"{split}-{label}"; rel=f"data/cases/{identifier}.json"
                    (root/rel).write_text(json.dumps({"text":identifier}))
                    rows.append({"schema_version":"2","id":identifier,"benchmark":"fixture","task_type":"text_classification","split":split,"input":rel,"output":json.dumps({"label":label}),"reasoning":"gold","metadata":"{}"})
            with (root/"evals.csv").open("w",newline="") as handle:
                writer=csv.DictWriter(handle,fieldnames=rows[0]); writer.writeheader(); writer.writerows(rows)
            (root/"selection.json").write_text(json.dumps({"dataset":"fixture","selected":[{"id":r["id"],"split":r["split"]} for r in rows],"sources":[]}))
            self.assertTrue(MODULE.audit(root)["passed"])

    def test_pilot_content_overlap_fails_audit(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            roots = [base / "current", base / "pilot"]
            for root in roots:
                (root/"data/cases").mkdir(parents=True)
                rows=[]
                for split in ("development","validation","test"):
                    for label in ("a","b"):
                        identifier=f"{root.name}-{split}-{label}"; rel=f"data/cases/{identifier}.json"
                        text = "shared" if split == "test" and label == "a" else identifier
                        (root/rel).write_text(json.dumps({"text":text}))
                        rows.append({"schema_version":"2","id":identifier,"benchmark":"fixture","task_type":"text_classification","split":split,"input":rel,"output":json.dumps({"label":label}),"reasoning":"gold","metadata":"{}"})
                with (root/"evals.csv").open("w",newline="") as handle:
                    writer=csv.DictWriter(handle,fieldnames=rows[0]); writer.writeheader(); writer.writerows(rows)
                (root/"selection.json").write_text(json.dumps({"dataset":"fixture","selected":[{"id":r["id"],"split":r["split"]} for r in rows],"sources":[],"excluded_datasets":[]}))
            proof = MODULE.audit(roots[0], pilot_datasets=[roots[1]])
            self.assertGreater(proof["checks"]["pilot_overlap_count"], 0)
            self.assertFalse(proof["passed"])

if __name__ == "__main__": unittest.main()
