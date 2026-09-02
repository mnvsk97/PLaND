import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "datasources.py"
SPEC = importlib.util.spec_from_file_location("evolved_datasources", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ExtractSignalsTests(unittest.TestCase):
    def test_fax_cover_sheet_is_form_signal(self):
        value = MODULE.extract_signals("TELECOPIER COVER SHEET\nTo: ; FAX NUMBER:\n[ ] Sent")
        self.assertGreater(value["form_terms"], 0)
        self.assertGreater(value["fillable_markers"], 0)

    def test_email_headers_are_counted(self):
        value = MODULE.extract_signals("From: A\nSent: Today\nTo: B\nSubject: Test")
        self.assertEqual(value["email_headers"], 4)


if __name__ == "__main__":
    unittest.main()
