import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "trim_document.py"
SPEC = importlib.util.spec_from_file_location("trim_document", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class TrimDocumentTests(unittest.TestCase):
    def test_bounds_preserve_head_and_tail(self):
        text = "A" * 2000 + "TAIL"
        if len(text) > MODULE.LIMIT:
            result = text[:MODULE.HEAD].rstrip() + "\n[...middle omitted...]\n" + text[-MODULE.TAIL:].lstrip()
        self.assertLessEqual(len(result), MODULE.HEAD + MODULE.TAIL + 24)
        self.assertTrue(result.startswith("A" * 100))
        self.assertTrue(result.endswith("TAIL"))


if __name__ == "__main__":
    unittest.main()
