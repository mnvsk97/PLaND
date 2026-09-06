import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1]/'scripts/prepare_fresh_collection.py'
SPEC = importlib.util.spec_from_file_location('fresh', SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FreshExposureTests(unittest.TestCase):
    def test_aggregate_pilot_and_partial_runs_are_excluded(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            experiment = root/'experiments/ledgar-text-classification'
            (experiment/'results').mkdir(parents=True)
            (experiment/'paper-subset.json').write_text(json.dumps({'selected':[{'id':'pilot'}]}))
            (experiment/'results/summary.json').write_text('{"cases":20}')
            run = root/'tmp/fresh-paper-fixture/runs/ledgar'
            run.mkdir(parents=True)
            (run/'test.partial.json').write_text(json.dumps({'cases':[{'id':'interrupted'}]}))
            ids, evidence = MODULE.historical_exposure([root,root], 'ledgar')
            self.assertEqual(ids, {'pilot','interrupted'})
            self.assertEqual(len(evidence), 2)
            self.assertTrue(any('execution_evidence' in item for item in evidence))


if __name__ == '__main__':
    unittest.main()
