"""Small independent fixtures for the manuscript audit's fail-closed checks."""
import copy
import unittest

from audit_paper import (OUT, REPEATS, accuracy_summaries, check, close, intervals,
                         mean_accuracy, mean_token_reduction, passages, pct, quantile,
                         read, summarize)


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

    def accuracy_rows(self):
        return [{'dataset': 'LEDGAR', 'stage': 'final-test', 'repeat': repeat,
                 'baseline': {'cases': 500, 'correct': correct},
                 'hybrid': {'cases': 500, 'correct': 479}}
                for repeat, correct in zip(REPEATS, (474, 475, 475))]

    def test_mean_uses_all_unrounded_case_counts(self):
        rows = self.accuracy_rows()
        self.assertAlmostEqual(mean_accuracy(rows, 'baseline'), 1424 / 1500)
        self.assertEqual(pct(mean_accuracy(rows, 'baseline'), 2), '94.93')
        self.assertEqual(pct(mean_accuracy(rows, 'hybrid'), 2), '95.80')
        summaries = accuracy_summaries(rows)
        self.assertEqual(summaries[0]['repeats'], 3)
        self.assertEqual(summaries[0]['cases_per_repeat'], 500)
        self.assertEqual(summaries[0]['baseline_mean_accuracy'], mean_accuracy(rows, 'baseline'))

    def test_mean_rejects_missing_or_duplicate_repeats(self):
        rows = self.accuracy_rows()
        with self.assertRaisesRegex(RuntimeError, 'incomplete accuracy repeats'):
            mean_accuracy(rows[:2], 'baseline')
        rows[-1]['repeat'] = rows[0]['repeat']
        with self.assertRaisesRegex(RuntimeError, 'incomplete accuracy repeats'):
            mean_accuracy(rows, 'baseline')

    def test_mean_rejects_mixed_splits_and_unequal_denominators(self):
        rows = self.accuracy_rows()
        rows[-1]['stage'] = 'selection'
        with self.assertRaisesRegex(RuntimeError, 'mixed accuracy group'):
            mean_accuracy(rows, 'baseline')
        rows = self.accuracy_rows()
        rows[-1]['baseline']['cases'] = 1000
        with self.assertRaisesRegex(RuntimeError, 'accuracy denominators'):
            mean_accuracy(rows, 'baseline')

    def test_token_reduction_mean_uses_all_three_runs(self):
        rows = copy.deepcopy(read(OUT / 'paper-calculations.json')['runs'])
        group = [r for r in rows if r['dataset'] == 'LEDGAR' and r['stage'] == 'final-test']
        expected = sum(r['token_reduction'] for r in group) / 3
        self.assertAlmostEqual(mean_token_reduction(group), expected)
        self.assertEqual(pct(mean_token_reduction(group), 2), '74.56')
        with self.assertRaisesRegex(RuntimeError, 'incomplete token-reduction repeats'):
            mean_token_reduction(group[:2])

    def test_mean_does_not_override_one_failed_gate(self):
        rows = copy.deepcopy(read(OUT / 'paper-calculations.json')['runs'])
        group = [r for r in rows if r['dataset'] == 'LEDGAR' and r['stage'] == 'selection']
        self.assertGreater(mean_accuracy(group, 'hybrid'), .8)
        group[0]['passed'] = False
        table = passages(rows)['selection_table']
        ledgar = next(line for line in table.splitlines() if line.startswith('| LEDGAR |'))
        self.assertTrue(ledgar.endswith('| Reject |'))

    def test_main_mean_and_individual_appendix_values(self):
        blocks = passages(read(OUT / 'paper-calculations.json')['runs'])
        self.assertIn('| Mean token reduction (%) |', blocks['selection_table'])
        self.assertIn('| Mean token reduction (%) |', blocks['final_table'])
        self.assertIn('LEDGAR, final-test, 500 cases | Mean accuracy: 94.93% → 95.80%', blocks['main_table'])
        self.assertIn('CFPB, selection, 1,000 cases | Mean accuracy: 79.73% → 79.27%', blocks['main_table'])
        self.assertNotIn('CFPB, final-test', blocks['main_table'])
        self.assertNotIn('interval', blocks['ledgar_result'])
        self.assertNotIn('interval', blocks['spam_result'])
        self.assertIn('| Mean accuracy B → H (%) |', blocks['final_table'])
        self.assertIn('| LEDGAR | 94.93 → 95.80 |', blocks['final_table'])
        self.assertIn('| LEDGAR | 94.93 → 95.80 | 500 → 130 | 74.56 |', blocks['final_table'])
        self.assertIn('| CFPB | 79.73 → 79.27 |', blocks['selection_table'])
        self.assertIn('| CFPB | 79.73 → 79.27 | 23.45 | Reject |', blocks['selection_table'])
        self.assertIn('| LEDGAR final test | 1 | 94.8 / 95.8 |', blocks['repeat_table'])
        self.assertIn('| LEDGAR final test | 1 | -0.40 to 2.60 |', blocks['interval_table'])


if __name__ == '__main__':
    unittest.main()
