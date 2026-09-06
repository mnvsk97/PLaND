from pathlib import Path
OPS = Path(__file__).resolve().parent
"""Prepare and measure one dataset after its predecessor has finished."""
import json
import os
import sys
from pathlib import Path
from operate import BASE,ROOT,PYTHON,CONTROLLER,RUNNER,controlled,call,baseline_gate

ds=sys.argv[1]
assert ds in {'cfpb','spamassassin'}, 'LEDGAR is already complete; do not resume its invalid reservation'
plan_path=ROOT/f'experiments/protocol/fresh-paper-{ds}.json'
plan=json.loads(plan_path.read_text())
os.environ.update(plan['runtime']['environment'])
os.environ['PYTHONUNBUFFERED']='1'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
dataset=BASE/'datasets'/ds
directory=BASE/'runs'/ds
packages=BASE/'packages'/ds
prepare=ROOT/'datasets/scripts/prepare_fresh_collection.py'
controlled(ds,'prepare','prepare-fresh-'+ds,[PYTHON,prepare,'--plan',plan_path,'--output',dataset],
           [plan_path,prepare,ROOT/'datasets/sources.lock.json'],[dataset])
controlled(ds,'prepare','generate-english-baseline',[PYTHON,OPS/'build_baseline.py','--dataset',dataset,'--output',packages],
           [OPS/'build_baseline.py',ROOT/'skills/generate-initial-version/scripts/generate.py'],[packages])
sources={'cfpb':Path('/Users/saikrishna/dev/deterministic-skills/tmp/confirmatory-datasets/cfpb/sources'),
         'spamassassin':Path('/Users/saikrishna/dev/deterministic-skills/tmp/enterprise-datasets/spamassassin/sources')}
audit=ROOT/'datasets/scripts/audit_prepared.py'
controlled(ds,'prepare','audit-fresh-'+ds,[PYTHON,audit,'--dataset',dataset,
           '--pilot-dataset',dataset.with_name(ds+'-prior-opened'),'--source-dir',sources[ds],
           '--output',directory/'dataset-audit.json'],[audit,dataset,dataset.with_name(ds+'-prior-opened')],[directory/'dataset-audit.json'])
controlled(ds,'prepare','independent-freshness-check',[PYTHON,OPS/'independent_freshness_check.py',
           '--dataset',dataset,'--output',directory/'independent-freshness.json'],
           [OPS/'independent_freshness_check.py',dataset,dataset.with_name(ds+'-prior-opened')],
           [directory/'independent-freshness.json'])
call([PYTHON,CONTROLLER,'complete-stage','--run-dir',directory,'--stage','prepare'])
package=packages/'baseline-01'
out=directory/'baseline-development-01.json'
controlled(ds,'baseline-development','baseline-attempt-01',[PYTHON,RUNNER,'--dataset',dataset,
           '--split','development','--system-prompt',package/'instructions.md',
           '--sop',package/f'skills/{ds}-classification/SKILL.md','--model','qwen3:14b',
           '--execution-backend','deepagent','--seed','20260902','--workers','2','--num-ctx','16384',
           '--num-predict','128','--keep-alive','-1','--candidate-id','baseline',
           '--attempt','1','--experiment-id',plan['study_id'],'--output',out,'--resume'],
           [package,RUNNER,RUNNER.with_name('deepagent_execution.py')],[out])
baseline_gate(ds)
state=json.loads((directory/'collection-state.json').read_text())
if state['decisions']['baseline-development'][-1]['value']!='ready':
    print('Baseline requires development-only refinement. No candidate or selection launched.')
    sys.exit(0)
candidate=BASE/'candidates'/ds/'candidate-01'
sop=package/f'skills/{ds}-classification/SKILL.md'
controlled(ds,'candidate-development','construct-candidate-01',[PYTHON,OPS/'build_candidate.py',
           '--dataset',dataset,'--baseline',sop,'--baseline-run',out,'--output',candidate],
           [OPS/'build_candidate.py',out,sop],[candidate])
script=ROOT/'skills/pland-evolver/scripts/sop_contract.py'
controlled(ds,'candidate-development','verify-candidate-contract',[PYTHON,script,'--baseline-sop',sop,
           '--candidate-sop',candidate/'SKILL.md','--output',directory/'candidate-contract.json'],
           [script,candidate],[directory/'candidate-contract.json'])
controlled(ds,'candidate-development','candidate-unit-checks',[PYTHON,OPS/'check_candidate.py',
           candidate/'classify.py',directory/'candidate-checks.json'],
           [OPS/'check_candidate.py',candidate/'classify.py'],[directory/'candidate-checks.json'])
call([PYTHON,OPS/'finish_dataset.py',ds])
