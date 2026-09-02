import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "select_subset.py"
SPEC = importlib.util.spec_from_file_location("select_subset", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class SelectionTests(unittest.TestCase):
    def test_proportional_allocation_is_bounded_and_exact(self):
        capacities = {"a": 80, "b": 200, "c": 720}
        allocation = MODULE.proportional_allocation(capacities, 900)
        self.assertEqual(sum(allocation.values()), 900)
        self.assertTrue(all(allocation[key] <= capacities[key] for key in capacities))

    def test_proportional_allocation_rejects_insufficient_capacity(self):
        with self.assertRaisesRegex(ValueError, "exceed"):
            MODULE.proportional_allocation({"a": 2}, 3)


if __name__ == "__main__":
    unittest.main()
