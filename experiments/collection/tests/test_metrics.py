import importlib.util
import json
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/run_experiment.py"
SPEC = importlib.util.spec_from_file_location("run_experiment", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)

class MetricsTests(unittest.TestCase):
    def test_macro_f1(self):
        cases = [{"expected":"a","actual":"a"},{"expected":"b","actual":"a"}]
        self.assertAlmostEqual(MODULE.macro_f1(cases, ["a","b"]), 1/3)

    def test_write_json_atomic_replaces_target(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            target = Path(directory) / "checkpoint.json"
            MODULE.write_json_atomic(target, {"value": 1})
            MODULE.write_json_atomic(target, {"value": 2})
            self.assertEqual(json.loads(target.read_text()), {"value": 2})
            self.assertFalse((target.parent / "checkpoint.json.tmp").exists())

if __name__ == "__main__": unittest.main()
