"""Apply the explicit author amendment at an unopened candidate boundary."""
import argparse
import importlib.util
import json
from pathlib import Path
from operate import ROOT, BASE, CONTROLLER

p=argparse.ArgumentParser();p.add_argument('dataset',choices=['cfpb']);a=p.parse_args()
spec=importlib.util.spec_from_file_location('controller',CONTROLLER)
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
d=BASE/'runs'/a.dataset
state,ledger=c.load_state(d)
assert not state['decisions']['candidate-development'] and not state['decisions']['selection']
assert not any(e['stage'] in {'candidate-development','selection','final-test'} for e in ledger['events'])
assert not any(e['status']=='running' for e in ledger['events'])
assert not c.git_value(ROOT,'status','--short'), 'Freeze amendment code and plans before applying'
old=c.load_json(Path(state['plan']['path']))
newpath=ROOT/f'experiments/protocol/fresh-paper-{a.dataset}-amended-20260906.json'
new=c.load_json(newpath);protocol=c.validate_plan(new,newpath,ROOT)
for key,value in old.items():
    if key not in {'protocol','limits'}: assert new[key]==value, key
assert new['limits']=={'baseline_attempts':10,'candidate_attempts':10}
receipt=ROOT/'experiments/protocol/candidate-budget-amendment-20260906.json'
entry={'recorded_at':c.now(),'git_head':c.git_value(ROOT,'rev-parse','HEAD'),
       'original_plan':state['plan'],'original_protocol':state['protocol'],
       'amended_plan':c.artifact(newpath),'amended_protocol':c.artifact(protocol),
       'authorization':c.artifact(receipt),'effective_after_event_count':len(ledger['events']),
       'baseline_decisions_preserved':len(state['decisions']['baseline-development']),
       'candidate_and_heldout_unopened':True}
assert not state.get('amendments') and not ledger.get('amendments')
state['amendments']=[entry];ledger['amendments']=[entry]
state['plan']=entry['amended_plan'];state['protocol']=entry['amended_protocol'];state['limits']=new['limits']
c.atomic_json(d/'protocol-amendment.json',entry)
c.atomic_json(d/'command-ledger.json',ledger)
c.atomic_json(d/'collection-state.json',state)
hold=d/'candidate-authorization-hold.json'
if hold.exists():
    preserved=d/'candidate-authorization-hold-resolved.json'
    assert not preserved.exists();hold.rename(preserved)
print(json.dumps(entry,indent=2))
