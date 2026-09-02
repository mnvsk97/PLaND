import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "compact_document.py"
SPEC = importlib.util.spec_from_file_location("compact_document", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class CompactDocumentTests(unittest.TestCase):
    def test_short_text_is_preserved(self):
        result = MODULE.compact("From: a@example.com\nSubject: Test")
        self.assertFalse(result["truncated"])
        self.assertEqual(result["text"], "From: a@example.com\nSubject: Test")

    def test_long_text_keeps_bounded_head_and_tail(self):
        result = MODULE.compact("A" * 4000 + "TAIL")
        self.assertTrue(result["truncated"])
        self.assertIn("middle omitted", result["text"])
        self.assertTrue(result["text"].endswith("TAIL"))
        self.assertLess(len(result["text"]), 3300)


if __name__ == "__main__":
    unittest.main()
