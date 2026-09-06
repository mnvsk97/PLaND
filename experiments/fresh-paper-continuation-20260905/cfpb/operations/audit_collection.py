from pathlib import Path
OPS = Path(__file__).resolve().parent
"""Audit fresh result arithmetic, frozen pairs, model work, and release order."""
import argparse
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--dataset', required=True)
p.add_argument('--output', required=True, type=Path)
a = p.parse_args()
ROOT = Path.cwd()
directory = ROOT/'tmp/fresh-paper-continuation-20260905/runs'/a.dataset
state = json.loads((directory/'collection-state.json').read_text())
plan = json.loads(Path(state['plan']['path']).read_text())
ledger = json.loads((directory/'command-ledger.json').read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
for field in ['plan','protocol']:
    assert sha(Path(state[field]['path'])) == state[field]['sha256']
assert state.get('amendments',[])==ledger.get('amendments',[])
for amendment in state.get('amendments',[]):
    for key in ['original_plan','original_protocol','amended_plan','amended_protocol','authorization']:
        artifact=amendment[key]
        assert sha(Path(artifact['path']))==artifact['sha256']
    boundary=amendment['effective_after_event_count']
    assert all(e['stage'] not in {'candidate-development','selection','final-test'} for e in ledger['events'][:boundary])
    assert all(e.get('plan_sha256')==state['plan']['sha256'] for e in ledger['events'][boundary:])
proof = json.loads((directory/'dataset-audit.json').read_text())
assert proof['passed'] and proof['counts']['by_split'] == {'development':500,'validation':1000,'test':500}
independent = json.loads((directory/'independent-freshness.json').read_text())
assert independent['passed']
assert not (directory/'collection-hold.json').exists()
dataset=ROOT/'tmp/fresh-paper-continuation-20260905/datasets'/a.dataset
with (dataset/'evals.csv').open() as handle: truth=list(csv.DictReader(handle))
truth_by_split={split:{r['id']:json.loads(r['output'])['label'] for r in truth if r['split']==split}
                for split in ['development','validation','test']}
spec=importlib.util.spec_from_file_location('controller',ROOT/'.codex/skills/pland-data-collection/scripts/run_collection.py')
controller=importlib.util.module_from_spec(spec);spec.loader.exec_module(controller)
checked_artifacts={}
for event in ledger['events']:
    for artifact in event.get('inputs',[])+event.get('outputs',[]):
        path=artifact['path']
        if path not in checked_artifacts: checked_artifacts[path]=controller.artifact(Path(path))['sha256']
        assert checked_artifacts[path]==artifact['sha256'], ('changed ledger artifact',path)
spec=importlib.util.spec_from_file_location('data_audit',ROOT/'datasets/scripts/audit_prepared.py')
data_audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(data_audit)
sources={'cfpb':Path('/Users/saikrishna/dev/deterministic-skills/tmp/confirmatory-datasets/cfpb/sources'),
         'spamassassin':Path('/Users/saikrishna/dev/deterministic-skills/tmp/enterprise-datasets/spamassassin/sources')}
rechecked=data_audit.audit(dataset,sources[a.dataset],[dataset.with_name(a.dataset+'-prior-opened')])
assert rechecked==proof and rechecked['passed']
runs = {}
for path in sorted(directory.glob('*.json')):
    value = json.loads(path.read_text())
    if not isinstance(value,dict) or not isinstance(value.get('cases'),list) or not value.get('model'):
        continue
    cases = value['cases']; summary = value['summary']; split = value['split']
    assert len(cases) == {'development':500,'validation':1000,'test':500}[split], path
    assert len({c['id'] for c in cases}) == len(cases), path
    assert {c['id']:c['expected'] for c in cases}==truth_by_split[split]
    assert value['invariants']['evals_sha256']==sha(dataset/'evals.csv')
    assert value['invariants']['selection_sha256']==sha(dataset/'selection.json')
    assert all(c['correct'] == (c['actual']==c['expected']) for c in cases), path
    for metric in ['input_tokens','output_tokens','total_tokens']:
        assert sum(c[metric] for c in cases) == summary[metric], (path,metric)
    assert sum(c['correct'] for c in cases)==summary['correct']
    assert summary['accuracy']==summary['correct']/len(cases)
    assert value['model_digest']==plan['model']['digest']
    assert value['model']==plan['model']['name']
    assert value['runtime']['execution_backend']=='deepagent'
    assert value['runtime']['workers']==2 and value['runtime']['num_ctx']==16384
    for key in ['think','stream','temperature','num_predict','keep_alive']:
        assert value['runtime'][key]==plan['runtime'][key]
    for key in ['OLLAMA_FLASH_ATTENTION','OLLAMA_KV_CACHE_TYPE','OLLAMA_NUM_PARALLEL','OLLAMA_MAX_LOADED_MODELS']:
        assert value['runtime'][key.lower()]==plan['runtime']['environment'][key]
    assert not summary['errors'] and summary['normal_completion_rate']==1
    assert summary['model_calls']==sum(c['model_calls'] for c in cases)
    for case in cases:
        if case['source']=='command':
            assert case['total_tokens']==0 and case['matched_rule']
            assert case['step_trace']['command_step_id']=='S03'
        else:
            assert case['deepagent_trace'] and case['model_calls']>=1
            trace = case['deepagent_trace']
            assert sum((m.get('usage_metadata') or {}).get('total_tokens',0) for m in trace)==case['total_tokens']
    runs[path.name]={'cases':len(cases),'accuracy':summary['accuracy'],'tokens':summary['total_tokens'],
                      'sha256':sha(path),'split':split,'seed':value['seed']}
selection = state['decisions']['selection']
candidate_history=state['decisions']['candidate-development']
assert len(candidate_history)<=plan['limits']['candidate_attempts']
assert len(selection)<=1
if candidate_history:
    assert all(d['value']=='refine' for d in candidate_history[:-1])
    if candidate_history[-1]['value']=='nonviable':
        assert len(candidate_history)==plan['limits']['candidate_attempts']
    if selection:
        assert candidate_history[-1]['value']=='ready'
        ready_at=candidate_history[-1]['recorded_at']
        assert all(e['started_at']>=ready_at for e in ledger['events'] if e['stage']=='selection')
        assert all(e['started_at']<ready_at for e in ledger['events'] if e['stage']=='candidate-development')
tests = [r for r in runs.values() if r['split']=='test']
if tests:
    assert selection and selection[-1]['value']=='accept'
    released_at = selection[-1]['recorded_at']
    assert all(e['started_at'] >= released_at for e in ledger['events'] if e['stage']=='final-test')
    assert len(tests)==8
    assert {r['seed'] for r in tests}=={20260902,20260903,20260904,20260905}
elif selection:
    assert selection[-1]['value']=='reject'
    assert len([r for r in runs.values() if r['split']=='validation'])==8
else:
    assert (state['decisions']['baseline-development'][-1]['value']=='nonviable'
            or state['decisions']['candidate-development'][-1]['value'] in {'reject','nonviable'})
spec=importlib.util.spec_from_file_location('compare',ROOT/'experiments/text-classification/scripts/compare.py')
compare=importlib.util.module_from_spec(spec);spec.loader.exec_module(compare)
verified=[]
for path in sorted(directory.glob('*-comparison.json')):
    if path.name.endswith('-sop-comparison.json'): continue
    saved=json.loads(path.read_text())
    parts=path.stem.split('-');split=parts[0];seed=int(parts[1])
    suffix='-'+'-'.join(parts[2:-1]) if len(parts)>3 else ''
    baseline = directory/f'{split}-{seed}-baseline.json'
    if split=='development':
        pointer=directory/'chosen-baseline.json'
        baseline=Path(json.loads(pointer.read_text())['run']) if pointer.exists() else directory/'baseline-development-01.json'
    n=json.loads(baseline.read_text())
    h=json.loads((directory/f'{split}-{seed}-hybrid{suffix}.json').read_text())
    assert n['invariants']==h['invariants'] and n['runtime']==h['runtime']
    nc={c['id']:c for c in n['cases']};hc={c['id']:c for c in h['cases']}
    assert nc.keys()==hc.keys()
    pairs=[(nc[k],hc[k]) for k in sorted(nc)]
    assert all(x['expected']==y['expected'] for x,y in pairs)
    for name,run in [('natural_language',n),('hybrid',h)]:
        cases=run['cases'];metric=saved[name]
        assert math.isclose(metric['macro_f1'],compare.macro_f1(cases),abs_tol=1e-12)
        assert saved['per_label_recall'][name]==compare.recall_by_label(cases)
        assert saved['paired_statistics'][name+'_accuracy_wilson_95']==compare.wilson_interval(sum(c['correct'] for c in cases),len(cases))
        assert math.isclose(metric['latency_seconds']['total'],sum(c['latency_seconds'] for c in cases),abs_tol=1e-9)
        assert math.isclose(metric['latency_seconds']['mean'],sum(c['latency_seconds'] for c in cases)/len(cases),abs_tol=1e-9)
    nl_only=sum(x['correct'] and not y['correct'] for x,y in pairs)
    h_only=sum(y['correct'] and not x['correct'] for x,y in pairs)
    assert saved['paired_statistics']['mcnemar_exact_p']==compare.mcnemar_exact(nl_only,h_only)
    assert saved['mechanism_decomposition']['command_routed_hybrid_precision']==compare.command_precision(h['cases'])
    for key,fn,offset in [('accuracy_difference_bootstrap_95',compare.accuracy_difference,0),
                          ('token_reduction_bootstrap_95',compare.token_reduction,1)]:
        actual=compare.paired_bootstrap(pairs,fn,5000,20260902+offset)
        assert actual==saved['paired_statistics'][key], (path,key)
    assert saved['natural_language']['total_tokens']==sum(c['total_tokens'] for c in n['cases'])
    assert saved['hybrid']['total_tokens']==sum(c['total_tokens'] for c in h['cases'])
    verified.append(path.name)
result={'status':'PASS','dataset':a.dataset,'dataset_audit_passed':True,'runs':runs,
        'transport_protocol_deviation':json.loads((directory/'runtime-audit.json').read_text())['transport_audit'],
        'ledger_artifact_hashes_reverified':len(checked_artifacts),'prepared_data_reaudited':True,
        'independent_freshness':independent,
        'statistically_recomputed_comparisons':verified,'final_test_release_verified':bool(tests),
        'final_test_unopened':not tests,'plan_sha256':state['plan']['sha256'],
        'failed_commands_preserved':sum(e['status']=='failed' for e in ledger['events'])}
if a.output.exists(): raise ValueError('Output exists')
a.output.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':'PASS','runs':len(runs),'comparisons':len(verified)}))
