import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1]/'scripts/prepare_collection.py'
SPEC = importlib.util.spec_from_file_location('fresh', SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FreshExposureTests(unittest.TestCase):
    def test_completed_and_partial_model_runs_are_excluded(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run = root/'experiments/model/2026-09-05-11-07-pm/ledgar/results'
            run.mkdir(parents=True)
            (run/'test.json').write_text(json.dumps({'cases':[{'id':'completed'}]}))
            (run/'test.partial.json').write_text(json.dumps({'cases':[{'id':'interrupted'}]}))
            ids, evidence = MODULE.historical_exposure([root,root], 'ledgar')
            self.assertEqual(ids, {'completed','interrupted'})
            self.assertEqual(len(evidence), 2)


if __name__ == '__main__':
    unittest.main()
