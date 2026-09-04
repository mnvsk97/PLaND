from __future__ import annotations

import importlib.util
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "paper" / "generate_tables.py"
SPEC = importlib.util.spec_from_file_location("generate_tables", MODULE_PATH)
assert SPEC and SPEC.loader
generate_tables = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generate_tables)


class FinalTableEvidenceTests(unittest.TestCase):
    def test_committed_snapshot_matches_evidence(self) -> None:
        self.assertTrue(generate_tables.check())

    def test_all_final_tables_are_generated(self) -> None:
        rendered = generate_tables.render()
        for number in range(1, 6):
            self.assertEqual(rendered.count(f"## Table {number}."), 1)

    def test_check_rejects_a_stale_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            stale = Path(directory) / "FINAL_TABLES.md"
            stale.write_text("stale table values\n", encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                self.assertFalse(generate_tables.check(stale))

    def test_high_value_final_claims_are_evidence_derived(self) -> None:
        rendered = generate_tables.render()
        for claim in (
            "376,088 -> 225,573 (-40.02%)",
            "376,090 -> 225,575.33 (-40.02%)",
            "93.6% -> 92.8%",
            "82/500 at 98.78% precision",
            "0.746 -> 0.715",
        ):
            self.assertIn(claim, rendered)


if __name__ == "__main__":
    unittest.main()
