import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "sop_contract.py"
SPEC = importlib.util.spec_from_file_location("sop_contract", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


BASELINE = """# SOP

1. [S01] Read the complete item. <!-- pland:english -->
2. [S02] Classify the item using the supplied labels. <!-- pland:english -->
3. [S03] Return the required JSON. <!-- pland:english -->
"""


def candidate(fallback: str, marker: str = "fallback=S02") -> str:
    return f"""# SOP

1. [S01] Read the complete item. <!-- pland:english -->
2. [S02] Run `python classify.py`. <!-- pland:command {marker} -->
   Fallback [S02]: {fallback} <!-- pland:fallback -->
3. [S03] Return the required JSON. <!-- pland:english -->
"""


class SopContractTests(unittest.TestCase):
    def test_accepts_exact_explicit_command_fallback_link(self):
        baseline = MODULE.baseline_contract(BASELINE)
        result = MODULE.validate_candidate(
            candidate("Classify the item using the supplied labels."), baseline
        )
        self.assertTrue(result["valid"])
        self.assertEqual(result["command_fallback_links"][0]["fallback_step_id"], "S02")

    def test_rejects_rewritten_fallback(self):
        with self.assertRaisesRegex(ValueError, "not the exact baseline instruction"):
            MODULE.validate_candidate(candidate("Classify it."), MODULE.baseline_contract(BASELINE))

    def test_rejects_unlinked_command(self):
        with self.assertRaisesRegex(ValueError, "must declare fallback=S02"):
            MODULE.validate_candidate(
                candidate("Classify the item using the supplied labels.", "fallback=S01"),
                MODULE.baseline_contract(BASELINE),
            )


if __name__ == "__main__":
    unittest.main()
