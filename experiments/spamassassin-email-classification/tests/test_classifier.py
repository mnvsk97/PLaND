import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "hybrid" / "classify.py"
SPEC = importlib.util.spec_from_file_location("spam_classifier", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ClassifierTests(unittest.TestCase):
    def test_routes_unambiguous_spam(self):
        message = "Subject: Trial offer\n\nTry our herbal Viagra product today."
        self.assertEqual(MODULE.classify(message, ["spam", "ham"])["label"], "spam")

    def test_defers_legitimate_or_ambiguous_mail(self):
        message = "Subject: Project update\n\nThe deployment review is Tuesday at 10."
        self.assertIsNone(MODULE.classify(message, ["ham", "spam"]))


if __name__ == "__main__":
    unittest.main()
