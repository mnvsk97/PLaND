from pathlib import Path
OPS = Path(__file__).resolve().parent
"""Complete the frozen candidate's permitted stages, without candidate revision."""
import json
import sys
from pathlib import Path
from operate import BASE, ROOT, PYTHON, CONTROLLER, call, model, compare, candidate_gate

ds = sys.argv[1]
directory = BASE/'runs'/ds
model(ds, 'candidate-development', 'hybrid', 20260902)
compare(ds, 'candidate-development', 20260902)
candidate_gate(ds, 'candidate-development')
state = json.loads((directory/'collection-state.json').read_text())
if state['decisions']['candidate-development'][-1]['value'] != 'ready':
    print('Candidate rejected on development; selection and final test remain unopened.')
    sys.exit(0)
for variant in ['baseline','hybrid']:
    model(ds, 'selection', variant, 20260902)
compare(ds, 'selection', 20260902)
candidate_gate(ds, 'selection')
release = json.loads((directory/'selection-release.json').read_text())
stage = 'final-test' if release['decision'] == 'accept' else 'selection'
if stage == 'final-test':
    for variant in ['baseline','hybrid']:
        model(ds, stage, variant, 20260902)
    compare(ds, stage, 20260902)
for index, seed in enumerate([20260903,20260904,20260905]):
    order = ['baseline','hybrid'] if index != 1 else ['hybrid','baseline']
    for variant in order:
        model(ds, stage, variant, seed)
    compare(ds, stage, seed)
if stage == 'final-test':
    call([PYTHON, CONTROLLER, 'complete-stage', '--run-dir', directory, '--stage', stage])
print(json.dumps({'dataset':ds, 'main_stage':stage, 'repeated_pairs':3, 'status':'model_collection_complete'}))
