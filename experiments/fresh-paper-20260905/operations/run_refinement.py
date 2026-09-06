"""Measure one approved-budget English-only clarification on development."""
import argparse
import json
import os
from pathlib import Path
from operate import BASE, ROOT, PYTHON, RUNNER, baseline, controlled, baseline_gate, call, plan_path

OPS=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('dataset');p.add_argument('--clarification',required=True,type=Path)
a=p.parse_args();ds=a.dataset;directory=BASE/'runs'/ds
state=json.loads((directory/'collection-state.json').read_text())
assert state['decisions']['baseline-development'][-1]['value']=='refine'
assert not state['decisions']['candidate-development']
info=baseline(ds);attempt=info['attempt']+1
assert attempt==len(state['decisions']['baseline-development'])+1 and attempt<=10
plan=json.loads(plan_path(ds).read_text())
os.environ.update(plan['runtime']['environment']);os.environ['PYTHONDONTWRITEBYTECODE']='1'
package=BASE/'refinements'/ds/f'baseline-{attempt:02}'
out=directory/f'baseline-development-{attempt:02}.json'
controlled(ds,'baseline-development',f'construct-baseline-{attempt:02}',
 [PYTHON,OPS/'refine_baseline.py','--previous',info['package'],'--previous-run',info['run'],
  '--clarification',a.clarification,'--output',package,'--dataset',ds,'--attempt',str(attempt)],
 [OPS/'refine_baseline.py',Path(info['package']),Path(info['run']),a.clarification],[package])
controlled(ds,'baseline-development',f'baseline-attempt-{attempt:02}',
 [PYTHON,RUNNER,'--dataset',BASE/'datasets'/ds,'--split','development','--system-prompt',package/'instructions.md',
  '--sop',package/f'skills/{ds}-classification/SKILL.md','--model',plan['model']['name'],
  '--execution-backend','deepagent','--seed','20260902','--workers','2','--num-ctx','16384',
  '--num-predict','128','--keep-alive','-1','--candidate-id','baseline','--attempt',str(attempt),
  '--experiment-id',plan['study_id'],'--output',out,'--resume'],
 [package,RUNNER,RUNNER.with_name('deepagent_execution.py')],[out])
# This operational pointer is not a frozen input; immutable per-attempt artifacts remain in the ledger.
(directory/'chosen-baseline.json').write_text(json.dumps({'attempt':attempt,'package':str(package),'run':str(out)},indent=2)+'\n')
baseline_gate(ds)
state=json.loads((directory/'collection-state.json').read_text())
if state['decisions']['baseline-development'][-1]['value']=='ready':
    call([PYTHON,OPS/'continue_ready.py',ds])
