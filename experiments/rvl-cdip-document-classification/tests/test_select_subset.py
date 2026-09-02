import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "select_subset.py"
SPEC = importlib.util.spec_from_file_location("select_subset", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class SelectSubsetTests(unittest.TestCase):
    def test_selection_is_balanced_and_deterministic(self):
        rows = []
        for label in range(len(MODULE.LABELS)):
            for offset in range(3):
                rows.append({"row_idx": label * 3 + offset, "row": {"label": label}})
        first = MODULE.select_rows(rows, 20260902, "validation")
        second = MODULE.select_rows(list(reversed(rows)), 20260902, "validation")
        self.assertEqual([item["row_idx"] for item in first], [item["row_idx"] for item in second])
        self.assertEqual({item["row"]["label"] for item in first}, set(range(16)))


if __name__ == "__main__":
    unittest.main()
