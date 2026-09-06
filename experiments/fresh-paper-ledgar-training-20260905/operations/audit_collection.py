from pathlib import Path
OPS = Path(__file__).resolve().parent
"""Audit fresh result arithmetic, frozen pairs, model work, and release order."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--dataset', required=True)
p.add_argument('--output', required=True, type=Path)
a = p.parse_args()
ROOT = Path.cwd()
directory = ROOT/'tmp/fresh-paper-ledgar-training-20260905/runs'/a.dataset
plan = json.loads((ROOT/f'experiments/protocol/fresh-paper-ledgar-training.json').read_text())
state = json.loads((directory/'collection-state.json').read_text())
ledger = json.loads((directory/'command-ledger.json').read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
for field in ['plan','protocol']:
    assert sha(Path(state[field]['path'])) == state[field]['sha256']
proof = json.loads((directory/'dataset-audit.json').read_text())
assert proof['passed'] and proof['counts']['by_split'] == {'development':500,'validation':1000,'test':500}
independent = json.loads((directory/'independent-freshness.json').read_text())
assert independent['passed']
assert not (directory/'collection-hold.json').exists()
runs = {}
for path in sorted(directory.glob('*.json')):
    value = json.loads(path.read_text())
    if not isinstance(value,dict) or not isinstance(value.get('cases'),list) or not value.get('model'):
        continue
    cases = value['cases']; summary = value['summary']; split = value['split']
    assert len(cases) == {'development':500,'validation':1000,'test':500}[split], path
    assert len({c['id'] for c in cases}) == len(cases), path
    assert all(c['correct'] == (c['actual']==c['expected']) for c in cases), path
    for metric in ['input_tokens','output_tokens','total_tokens']:
        assert sum(c[metric] for c in cases) == summary[metric], (path,metric)
    assert sum(c['correct'] for c in cases)==summary['correct']
    assert summary['accuracy']==summary['correct']/len(cases)
    assert value['model_digest']==plan['model']['digest']
    assert value['runtime']['execution_backend']=='deepagent'
    assert value['runtime']['workers']==2 and value['runtime']['num_ctx']==16384
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
            or state['decisions']['candidate-development'][-1]['value']=='reject')
spec=importlib.util.spec_from_file_location('compare',ROOT/'experiments/text-classification/scripts/compare.py')
compare=importlib.util.module_from_spec(spec);spec.loader.exec_module(compare)
verified=[]
for path in sorted(directory.glob('*-comparison.json')):
    if path.name.endswith('-sop-comparison.json'): continue
    saved=json.loads(path.read_text())
    split,seed,_=path.stem.split('-'); seed=int(seed)
    baseline = directory/f'{split}-{seed}-baseline.json'
    if split=='development':
        pointer=directory/'chosen-baseline.json'
        baseline=Path(json.loads(pointer.read_text())['run']) if pointer.exists() else directory/'baseline-development-01.json'
    n=json.loads(baseline.read_text())
    h=json.loads((directory/f'{split}-{seed}-hybrid.json').read_text())
    assert n['invariants']==h['invariants'] and n['runtime']==h['runtime']
    nc={c['id']:c for c in n['cases']};hc={c['id']:c for c in h['cases']}
    assert nc.keys()==hc.keys()
    pairs=[(nc[k],hc[k]) for k in sorted(nc)]
    assert all(x['expected']==y['expected'] for x,y in pairs)
    for key,fn,offset in [('accuracy_difference_bootstrap_95',compare.accuracy_difference,0),
                          ('token_reduction_bootstrap_95',compare.token_reduction,1)]:
        actual=compare.paired_bootstrap(pairs,fn,5000,20260902+offset)
        assert actual==saved['paired_statistics'][key], (path,key)
    assert saved['natural_language']['total_tokens']==sum(c['total_tokens'] for c in n['cases'])
    assert saved['hybrid']['total_tokens']==sum(c['total_tokens'] for c in h['cases'])
    verified.append(path.name)
result={'status':'PASS','dataset':a.dataset,'dataset_audit_passed':True,'runs':runs,
        'statistically_recomputed_comparisons':verified,'final_test_release_verified':bool(tests),
        'final_test_unopened':not tests,'plan_sha256':state['plan']['sha256'],
        'failed_commands_preserved':sum(e['status']=='failed' for e in ledger['events'])}
if a.output.exists(): raise ValueError('Output exists')
a.output.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':'PASS','runs':len(runs),'comparisons':len(verified)}))
