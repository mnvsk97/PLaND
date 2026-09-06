"""Construct the single allowed candidate from the ready English baseline."""
import json
import sys
from pathlib import Path
from operate import BASE, ROOT, PYTHON, CONTROLLER, baseline, controlled, call

OPS=Path(__file__).resolve().parent
ds=sys.argv[1];directory=BASE/'runs'/ds
hold=directory/'candidate-authorization-hold.json'
if hold.exists():
    print(json.dumps({'status':'paused_before_candidate','hold':str(hold)}))
    sys.exit(0)
state=json.loads((directory/'collection-state.json').read_text())
assert state['decisions']['baseline-development'][-1]['value']=='ready'
assert not state['decisions']['candidate-development']
info=baseline(ds);package=Path(info['package']);out=Path(info['run'])
sop=package/f'skills/{ds}-classification/SKILL.md'
candidate=BASE/'candidates'/ds/'candidate-01'
controlled(ds,'candidate-development','construct-candidate-01',
 [PYTHON,OPS/'build_candidate.py','--dataset',BASE/'datasets'/ds,'--baseline',sop,'--baseline-run',out,'--output',candidate],
 [OPS/'build_candidate.py',out,sop],[candidate])
script=ROOT/'skills/pland-evolver/scripts/sop_contract.py'
controlled(ds,'candidate-development','verify-candidate-contract',
 [PYTHON,script,'--baseline-sop',sop,'--candidate-sop',candidate/'SKILL.md','--output',directory/'candidate-contract.json'],
 [script,candidate],[directory/'candidate-contract.json'])
controlled(ds,'candidate-development','candidate-unit-checks',
 [PYTHON,OPS/'check_candidate.py',candidate/'classify.py',directory/'candidate-checks.json'],
 [OPS/'check_candidate.py',candidate/'classify.py'],[directory/'candidate-checks.json'])
call([PYTHON,OPS/'finish_dataset.py',ds])
