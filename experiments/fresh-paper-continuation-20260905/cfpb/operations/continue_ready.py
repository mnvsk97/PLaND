"""Construct one bounded development attempt; first ready candidate alone advances."""
import argparse
import json
import sys
from pathlib import Path
from operate import BASE, ROOT, PYTHON, CONTROLLER, baseline, controlled, call, plan_path

OPS=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('dataset');p.add_argument('--builder',type=Path,default=OPS/'build_candidate.py')
a=p.parse_args();ds=a.dataset;directory=BASE/'runs'/ds
hold=directory/'candidate-authorization-hold.json'
if hold.exists():
    print(json.dumps({'status':'paused_before_candidate','hold':str(hold)}))
    sys.exit(0)
state=json.loads((directory/'collection-state.json').read_text())
assert state['decisions']['baseline-development'][-1]['value']=='ready'
history=state['decisions']['candidate-development']
assert not history or history[-1]['value']=='refine'
assert not state['decisions']['selection']
attempt=len(history)+1
assert attempt<=json.loads(plan_path(ds).read_text())['limits']['candidate_attempts']
if attempt>1:
    assert a.builder.resolve()!=(OPS/'build_candidate.py').resolve(), 'Review development traces and supply a bounded revised builder, not an unchanged rerun'
info=baseline(ds);package=Path(info['package']);out=Path(info['run'])
sop=package/f'skills/{ds}-classification/SKILL.md'
cid=f'candidate-{attempt:02}';candidate=BASE/'candidates'/ds/cid
suffix='' if attempt==1 else '-'+cid
controlled(ds,'candidate-development','construct-'+cid,
 [PYTHON,a.builder,'--dataset',BASE/'datasets'/ds,'--baseline',sop,'--baseline-run',out,'--output',candidate,'--candidate-id',cid],
 [a.builder,out,sop],[candidate])
(directory/'chosen-candidate.json').write_text(json.dumps({'attempt':attempt,'candidate_id':cid,'package':str(candidate)},indent=2)+'\n')
script=ROOT/'skills/pland-evolver/scripts/sop_contract.py'
controlled(ds,'candidate-development','verify-candidate-contract'+suffix,
 [PYTHON,script,'--baseline-sop',sop,'--candidate-sop',candidate/'SKILL.md','--output',directory/f'candidate-contract{suffix}.json'],
 [script,candidate],[directory/f'candidate-contract{suffix}.json'])
controlled(ds,'candidate-development','candidate-unit-checks'+suffix,
 [PYTHON,OPS/'check_candidate.py',candidate/'classify.py',directory/f'candidate-checks{suffix}.json'],
 [OPS/'check_candidate.py',candidate/'classify.py'],[directory/f'candidate-checks{suffix}.json'])
call([PYTHON,OPS/'finish_dataset.py',ds])
