from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "experiments/ledgar-accuracy-recovery/preflight.py"
SPEC = importlib.util.spec_from_file_location("ledgar_recovery_preflight", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class PreflightTests(unittest.TestCase):
    def test_committed_snapshot_supports_only_750_fresh_balanced_test_cases(self):
        protocol = json.loads((SCRIPT.parent / "protocol.json").read_text())
        proof = json.loads((ROOT / protocol["dataset"]["capacity_proof"]).read_text())
        result = MODULE.capacity(protocol, proof)
        test = result["splits"]["test"]
        self.assertTrue(result["feasible"])
        self.assertEqual(test["limiting_label"], "Terms")
        self.assertEqual(test["limiting_remaining_per_label"], 75)
        self.assertEqual(test["maximum_balanced_cases"], 750)


if __name__ == "__main__":
    unittest.main()
