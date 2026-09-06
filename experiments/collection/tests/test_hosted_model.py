"""Offline contract tests: every HTTP request is intercepted by MockTransport."""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

for key, value in {
    'MODEL_BASE_URL': 'https://provider.example/v1',
    'MODEL_NAME': 'vendor/fixture-model',
    'MODEL_PROVIDER_NAME': 'fixture-provider',
    'MODEL_PROVIDER_ENDPOINT': 'fixture-endpoint',
    'MODEL_REASONING_EFFORT': 'minimal',
    'MODEL_EXTRA_BODY_JSON': json.dumps({
        'reasoning': {'effort': 'minimal'},
        'provider': {'only': ['fixture-endpoint'], 'allow_fallbacks': False,
                     'require_parameters': True},
    }),
}.items():
    os.environ.setdefault(key, value)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import hosted_execution as OR
import deepagent_execution as DE
import run_experiment as RUN
import test_run_preflight


def completion(content='{"label":"a"}', **updates):
    data = {
        'id': 'gen-fixture', 'object': 'chat.completion', 'created': 1,
        'model': OR.MODEL, 'provider': 'Fixture Provider',
        'choices': [{'index': 0, 'finish_reason': 'stop', 'message': {
            'role': 'assistant', 'content': content,
            'reasoning_details': [{'type': 'reasoning.encrypted', 'data': 'opaque-fixture', 'index': 0}]}}],
        'usage': {'prompt_tokens': 120, 'completion_tokens': 30, 'total_tokens': 150,
                  'completion_tokens_details': {'reasoning_tokens': 22},
                  'prompt_tokens_details': {'cached_tokens': 40}, 'cost': 0.000111},
    }
    data.update(updates)
    return data


class UsageTests(unittest.TestCase):
    def test_reasoning_not_double_counted(self):
        usage = OR.normalize_usage(completion()['usage'])
        self.assertEqual(usage['total_tokens'], 150)
        self.assertEqual(usage['output_tokens'], 30)
        self.assertEqual(usage['reasoning_tokens'], 22)

    def test_missing_usage_is_not_zero(self):
        for usage in (None, {}, {'prompt_tokens': 1, 'completion_tokens': 1}):
            with self.assertRaises(ValueError):
                OR.normalize_usage(usage)

    def test_optional_fields_remain_unknown(self):
        value = OR.normalize_usage({'prompt_tokens': 10, 'completion_tokens': 2, 'total_tokens': 12})
        self.assertIsNone(value['reasoning_tokens'])
        self.assertIsNone(value['service_cost_usd'])

    def test_usage_inconsistency_rejected(self):
        usage = completion()['usage']
        usage['completion_tokens_details']['reasoning_tokens'] = 31
        with self.assertRaises(ValueError):
            OR.normalize_usage(usage)

    def test_provider_config_is_frozen_and_secret_free(self):
        config = OR.HostedConfig(4096)
        self.assertEqual(config.contract()['reasoning_effort'], 'minimal')
        self.assertFalse(config.contract()['seed_supported'])
        self.assertIsNone(config.identity()['weight_digest'])
        self.assertEqual(config.identity()['provider'], 'fixture-provider')
        self.assertNotIn('api_key', json.dumps(config.identity()))

    def test_output_namespace(self):
        OR.validate_output_path(Path('/tmp') / OR.MODEL_DIRECTORY / '2026-09-05-11-07-pm/ledgar/results/baseline.json')
        for path in ('/tmp/local-model/ledgar/results/run.json',
                     f'/tmp/{OR.MODEL_DIRECTORY}/collection/ledgar/results/run.json'):
            with self.assertRaises(ValueError):
                OR.validate_output_path(Path(path))


class TransportTests(unittest.TestCase):
    def setUp(self):
        import httpx
        self.env = patch.dict(os.environ, {'MODEL_API_KEY': 'fixture-not-a-real-key'})
        self.env.start()
        self.requests = []
        self.payload = completion()
        def handler(request):
            self.requests.append(json.loads(request.content))
            return httpx.Response(200, json=self.payload)
        self.http = httpx.Client(transport=httpx.MockTransport(handler))
        self.config = OR.HostedConfig(4096)
        self.llm = OR.build_model(self.config, ['a', 'b'], http_client=self.http)

    def tearDown(self):
        DE.build_agent.cache_clear()
        self.http.close()
        self.env.stop()

    def test_actual_chatopenai_serialization_and_roundtrip(self):
        from langchain_core.messages import HumanMessage
        answer = self.llm.invoke('one case')
        receipt = answer.response_metadata['hosted']
        self.assertEqual(receipt['usage']['cost'], 0.000111)
        details = answer.additional_kwargs['reasoning_details']
        self.llm.invoke([HumanMessage('one case'), answer, HumanMessage('continue same case')])
        body = self.requests[0]
        self.assertEqual(body['model'], OR.MODEL)
        self.assertEqual(body['reasoning'], {'effort': 'minimal'})
        self.assertEqual(body['provider'], {'only': ['fixture-endpoint'],
                                          'allow_fallbacks': False, 'require_parameters': True})
        self.assertEqual(body['max_tokens'], 4096)
        self.assertEqual(body['response_format']['type'], 'json_schema')
        self.assertNotIn('temperature', body)
        self.assertNotIn('seed', body)
        self.assertFalse(body['stream'])
        self.assertEqual(self.requests[1]['messages'][1]['reasoning_details'], details)
        normalized = OR.normalize_messages([answer])
        self.assertEqual(normalized['eval_count'], 30)

    def test_actual_deepagent_has_no_tools_and_cases_are_isolated(self):
        with patch.object(OR, 'build_model', return_value=self.llm):
            with ThreadPoolExecutor(max_workers=3) as pool:
                answers = list(pool.map(lambda text: DE.invoke(
                    OR.MODEL, 'Classify.', text, ['a', 'b'], self.config),
                    ['document-one', 'document-two', 'document-three']))
        self.assertEqual(len(self.requests), 3)
        for request in self.requests:
            self.assertFalse(request.get('tools'))
            humans = [m for m in request['messages'] if m['role'] == 'user']
            self.assertEqual(len(humans), 1)
            self.assertFalse(any(m['role'] == 'assistant' for m in request['messages']))
        for value, raw in answers:
            self.assertEqual(value, {'label': 'a'})
            self.assertEqual(raw['model_calls'], 1)
            self.assertEqual(raw['reasoning_tokens'], 22)

    def test_invalid_extra_fields_and_refusal(self):
        self.payload = completion('{"label":"a","extra":"invalid"}')
        with patch.object(OR, 'build_model', return_value=self.llm):
            value, _ = DE.invoke(OR.MODEL, 'Classify.', 'item', ['a'], self.config)
        self.assertEqual(value, {})

    def test_missing_key_fails_before_http(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, 'MODEL_API_KEY'):
                OR.build_model(self.config, ['a'])
        self.assertEqual(self.requests, [])


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.output = self.root / OR.MODEL_DIRECTORY / '2026-09-05-11-07-pm/ledgar/results/baseline.json'
        dataset, baseline, candidate, classifier, system = test_run_preflight.RunPreflightTests().fixture(
            self.root, 'Classify the item using the supplied labels.')
        self.candidate, self.classifier, self.baseline = candidate, classifier, baseline
        self.argv = [str(RUN.__file__), '--dataset', str(dataset), '--split', 'development',
                     '--system-prompt', str(system), '--sop', str(baseline),
                     '--max-completion-tokens', '4096',
                     '--workers', '3', '--output', str(self.output)]
        self.raw = {'message': {'content': '{"label":"a"}'}, 'prompt_eval_count': 120,
                    'eval_count': 30, 'model_calls': 1, 'done_reason': 'stop',
                    'reasoning_tokens': 22, 'cached_input_tokens': 0, 'service_cost_usd': 0.000111,
                    'request_receipts': [{'id': 'gen-one', 'provider': 'Fixture Provider', 'model': OR.MODEL}]}

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self, more=(), **kwargs):
        with patch.object(sys, 'argv', self.argv + list(more)), \
             patch.dict(os.environ, {'MODEL_API_KEY': 'fixture-not-a-real-key'}), \
             patch.object(DE, 'invoke', **kwargs) as call, contextlib.redirect_stdout(io.StringIO()):
            result = RUN.main()
        return result, call

    def test_hosted_preflight_is_offline(self):
        result, call = self.run_cli(['--preflight-only'])
        self.assertEqual(result, 0)
        call.assert_not_called()
        data = json.loads(self.output.read_text())
        self.assertEqual(data['runtime']['workers'], 3)
        self.assertEqual(data['runtime']['reasoning_effort'], 'minimal')

    def test_baseline_and_fallback_use_same_request(self):
        _, baseline_call = self.run_cli(return_value=({'label': 'a'}, self.raw))
        data = json.loads(self.output.read_text())
        self.assertIsNone(data['model_digest'])
        self.assertEqual(data['summary']['total_tokens'], 150)
        self.assertEqual(data['summary']['service_cost_usd'], 0.000111)
        self.classifier.write_text('def classify(text, labels):\n    return None\n')
        self.output = self.output.with_name('hybrid.json')
        self.argv[self.argv.index('--output') + 1] = str(self.output)
        self.argv[self.argv.index('--sop') + 1] = str(self.candidate)
        _, hybrid_call = self.run_cli(['--classifier', str(self.classifier), '--baseline-sop',
                                       str(self.baseline), '--command-step-id', 'S02'],
                                      return_value=({'label': 'a'}, self.raw))
        self.assertEqual(baseline_call.call_args, hybrid_call.call_args)

    def test_command_bypass_does_not_call_model(self):
        self.argv[self.argv.index('--sop') + 1] = str(self.candidate)
        _, call = self.run_cli(['--classifier', str(self.classifier), '--baseline-sop',
                                str(self.baseline), '--command-step-id', 'S02'])
        call.assert_not_called()
        result = json.loads(self.output.read_text())
        self.assertEqual(result['summary']['total_tokens'], 0)
        self.assertEqual(result['summary']['service_cost_usd'], 0)

    def test_failure_is_redacted_and_checkpoint_can_resume(self):
        with self.assertRaises(RuntimeError):
            self.run_cli(side_effect=RuntimeError('SECRET-MUST-NOT-APPEAR'))
        receipts = self.output.parent / (self.output.name + '.attempts')
        self.assertNotIn('SECRET-MUST-NOT-APPEAR', ''.join(p.read_text() for p in receipts.glob('*.json')))
        self.assertTrue(self.output.with_suffix('.json.partial.json').exists())
        result, _ = self.run_cli(['--resume'], return_value=({'label': 'a'}, self.raw))
        self.assertEqual(result, 0)
        self.assertEqual(len(list(receipts.glob('*.json'))), 2)

    def test_resume_rejects_changed_endpoint(self):
        with self.assertRaises(RuntimeError):
            self.run_cli(side_effect=RuntimeError('network failed'))
        with patch.object(OR, 'PROVIDER_ENDPOINT', 'different-endpoint'):
            with self.assertRaisesRegex(SystemExit, 'checkpoint does not match'):
                self.run_cli(['--resume'])


if __name__ == '__main__':
    unittest.main()
