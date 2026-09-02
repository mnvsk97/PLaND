import importlib.util
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

if __name__ == "__main__": unittest.main()
