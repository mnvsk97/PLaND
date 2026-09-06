from pathlib import Path
OPS = Path(__file__).resolve().parent
"""Export safe fixed run evidence, excluding licensed benchmark inputs."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('--dataset',required=True)
p.add_argument('--receipt',required=True,type=Path)
a=p.parse_args()
ROOT=Path.cwd();BASE=ROOT/'tmp/fresh-paper-ledgar-training-20260905'
output=ROOT/'experiments/fresh-paper-ledgar-training-20260905'/a.dataset
if output.exists(): raise ValueError('Export exists; inspect before replacing evidence')
output.mkdir(parents=True)
def copy(source,destination):
    destination.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,destination)
for path in (BASE/'runs'/a.dataset).glob('*.json'):
    if path.name not in {'collection-state.json','command-ledger.json','evidence-manifest.json'} and not path.name.endswith('.partial.json'):
        copy(path,output/'results'/path.name)
shutil.copytree(BASE/'runs'/a.dataset/'logs',output/'logs')
for name in ['generated','baseline-01']:
    source=BASE/'packages'/a.dataset/name
    if source.exists(): shutil.copytree(source,output/'packages'/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
candidate=BASE/'candidates'/a.dataset/'candidate-01'
if candidate.exists(): shutil.copytree(candidate,output/'packages/candidate-01',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
for path in (BASE/'packages'/a.dataset).glob('*.json'): copy(path,output/'construction'/path.name)
for path in OPS.glob('*.py'): copy(path,output/'operations'/path.name)
for path in [ROOT/f'experiments/protocol/fresh-paper-ledgar-training.json',ROOT/'experiments/protocol/fresh-paper-ledgar-training.md',
             BASE/'datasets'/a.dataset/'freshness-receipt.json',BASE/'datasets'/a.dataset/'selection.json']:
    copy(path,output/'protocol'/path.name)
for path in ['experiments/text-classification/scripts/run_experiment.py','experiments/text-classification/scripts/deepagent_execution.py',
             'experiments/text-classification/scripts/compare.py','skills/pland-evolver/scripts/assess_candidate.py',
             'skills/pland-evolver/scripts/compare_variants.py','skills/pland-evolver/scripts/sop_contract.py',
             '.codex/skills/pland-data-collection/scripts/run_collection.py','reproduce/uv.lock']:
    copy(ROOT/path,output/'implementation'/Path(path).name)
label_source=Path('/Users/saikrishna/dev/deterministic-skills/tmp/confirmatory-datasets/ledgar/selection.json')
frozen_plan=json.loads((ROOT/'experiments/protocol/fresh-paper-ledgar-training.json').read_text())
selection=json.loads((BASE/'datasets'/a.dataset/'selection.json').read_text())
assert selection['labels']==json.loads(label_source.read_text())['labels']
(output/'protocol/path-resolution.json').write_text(json.dumps({
    'field':'sampling.labels_from',
    'frozen_plan_reference':frozen_plan['sampling']['labels_from'],
    'resolved_actual_input':str(label_source),
    'resolved_sha256':hashlib.sha256(label_source.read_bytes()).hexdigest(),
    'labels':selection['labels'],
    'note':'The descriptive reference path in the frozen plan was absent. The recorded preparer argv used the existing confirmatory selection manifest, preserving the exact same ten labels. No plan bytes, labels, outputs or sampling settings were changed.'
},indent=2)+'\n')
(output/'README.md').write_text(f'''# {a.dataset} fresh collection evidence

The approved split is 500 development / 1,000 selection / 500 final test.
Read `results/collection-audit.json` and the recorded selection release before
interpreting any outcome. Missing final-test files mean the test was unopened.
The run JSON contains safe classification outputs and model response metadata;
licensed source documents and expected-answer CSVs remain in the local data
directory and are represented here by hashes and provenance.

The archived commands retain their original absolute paths. Exact reruns need
the locked source bytes and path resolution to a new checkout. The `generated`
package is the initial skill output; `baseline-01` is the English package used
by the fixed request harness in `implementation/deepagent_execution.py`.
All model-mediated work uses Qwen through `create_deep_agent`; direct command
routes use the frozen classifier and invoke that identical English fallback
on abstention. No result is an autonomous rule-discovery reliability estimate.
''')
files=[]
for path in sorted(output.rglob('*')):
    if path.is_file(): files.append({'path':str(path.relative_to(output)), 'bytes':path.stat().st_size,
                                    'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
stable_files=[item for item in files if not item['path'].startswith('logs/')]
receipt={'dataset':a.dataset,'export':str(output),'files':stable_files,'raw_benchmark_inputs_exported':False,
         'log_disposition':'Logs are finalized and hashed by the final collection manifest, after the export command closes.'}
(output/'case-evidence-manifest.json').write_text(json.dumps({'schema_version':1,'files':stable_files},indent=2)+'\n')
a.receipt.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'export':str(output),'files':len(files)}))
