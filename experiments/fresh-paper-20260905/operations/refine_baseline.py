"""Save one development-grounded English clarification without changing the prompt."""
import argparse
import difflib
import hashlib
import importlib.util
import json
import shutil
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('--previous',required=True,type=Path)
p.add_argument('--previous-run',required=True,type=Path)
p.add_argument('--clarification',required=True,type=Path)
p.add_argument('--output',required=True,type=Path)
p.add_argument('--dataset',required=True)
p.add_argument('--attempt',required=True,type=int)
a=p.parse_args()
assert 2 <= a.attempt <= 10 and not a.output.exists()
run=json.loads(a.previous_run.read_text())
assert run['split']=='development' and run['candidate_id']=='baseline'
change=json.loads(a.clarification.read_text())
assert change['based_on_run']==a.previous_run.name
assert change['step_id'] in {'S01','S02','S03','S04'}
assert '<!--' not in change['instruction'] and '\n' not in change['instruction']
shutil.copytree(a.previous,a.output,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
sop=a.output/f'skills/{a.dataset}-classification/SKILL.md'
old=sop.read_text();lines=old.splitlines()
matches=[i for i,line in enumerate(lines) if f"[{change['step_id']}]" in line]
assert len(matches)==1
i=matches[0];prefix=lines[i].split('] ',1)[0]+'] '
lines[i]=prefix+change['instruction']+' <!-- pland:english -->'
new='\n'.join(lines)+'\n';sop.write_text(new)
spec=importlib.util.spec_from_file_location('generate',Path.cwd()/'skills/generate-initial-version/scripts/generate.py')
generate=importlib.util.module_from_spec(spec);spec.loader.exec_module(generate)
contract=generate.baseline_sop_contract(new)
cp=a.output/'data/baseline-sop-contract.json';cp.write_text(json.dumps(contract,indent=2)+'\n')
mp=a.output/'data/manifest.json';manifest=json.loads(mp.read_text())
manifest['baseline_sop_contract'].update(sha256=hashlib.sha256(cp.read_bytes()).hexdigest(),contract_sha256=contract['contract_sha256'])
mp.write_text(json.dumps(manifest,indent=2)+'\n')
assert (a.output/'instructions.md').read_bytes()==(a.previous/'instructions.md').read_bytes()
(a.output/'refinement.json').write_text(json.dumps({
 'attempt':a.attempt,'methodology_skill':'generate-initial-version','model':'gpt-6-astra','reasoning':'high',
 'previous_run_sha256':hashlib.sha256(a.previous_run.read_bytes()).hexdigest(),
 'development_only':True,'selection_or_test_used':False,'system_prompt_unchanged':True,
 'clarification':change,'diff':list(difflib.unified_diff(old.splitlines(),new.splitlines()))},indent=2)+'\n')
print(json.dumps({'baseline':str(a.output),'attempt':a.attempt,'sop_sha256':hashlib.sha256(sop.read_bytes()).hexdigest()}))
