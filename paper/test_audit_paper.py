"""Small independent fixtures for the manuscript audit's fail-closed checks."""
import copy
import unittest

from audit_paper import check, close, intervals, quantile, summarize


class PaperAuditTests(unittest.TestCase):
    def fixture(self):
        return {'cases': [{'id':'a', 'expected':'ham', 'actual':'ham', 'correct':True,
                           'input_tokens':10, 'output_tokens':2, 'total_tokens':12, 'model_calls':1}],
                'summary':{'cases':1,'correct':1,'accuracy':1.,'input_tokens':10,'output_tokens':2,
                           'total_tokens':12,'model_calls':1,'errors':{}},
                'runtime':{'seed_supported':False,'workers':8}, 'observed_providers':['Google AI Studio']}

    def test_summary_derived_from_cases(self):
        self.assertEqual(summarize(self.fixture())['total_tokens'], 12)

    def test_wrong_correctness_rejected(self):
        run = self.fixture()
        run['cases'][0]['actual'] = 'Ham'
        with self.assertRaisesRegex(RuntimeError, 'correctness'):
            summarize(run)

    def test_wrong_tokens_rejected(self):
        run = self.fixture()
        run['summary']['total_tokens'] = 11
        with self.assertRaisesRegex(RuntimeError, 'summary'):
            summarize(run)

    def test_duplicates_rejected(self):
        run = self.fixture()
        run['cases'].append(copy.deepcopy(run['cases'][0]))
        with self.assertRaisesRegex(RuntimeError, 'duplicate'):
            summarize(run)

    def test_literal_label_and_constant_bootstrap(self):
        b = self.fixture()['cases'][0]
        h = dict(b, actual='Ham', correct=False, input_tokens=0, output_tokens=0, total_tokens=0)
        accuracy, tokens = intervals([(b,h)], 20, 7)
        self.assertEqual(accuracy, [-1., -1.])
        self.assertEqual(tokens, [1., 1.])

    def test_quantile_interpolation(self):
        self.assertEqual(quantile([0, 10], .25), 2.5)
        self.assertTrue(close([1., 2.], [1., 2.]))
        self.assertFalse(close([1.], [1., 2.]))

    def test_check_not_disabled_by_optimization(self):
        with self.assertRaises(RuntimeError):
            check(False, 'must fail')


if __name__ == '__main__':
    unittest.main()
