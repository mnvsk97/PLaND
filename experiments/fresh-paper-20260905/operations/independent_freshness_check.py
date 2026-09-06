"""Reconcile all historical exposure against exclusions before model evaluation."""
import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--dataset', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
root = Path.cwd()
spec = importlib.util.spec_from_file_location('fresh', root/'datasets/scripts/prepare_fresh_collection.py')
fresh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fresh)
def rows(path):
    with path.open() as handle:
        return list(csv.DictReader(handle))
selected = rows(a.dataset/'evals.csv')
excluded = rows(a.dataset.with_name(a.dataset.name+'-prior-opened')/'evals.csv')
selected_ids = {r['id'] for r in selected}
excluded_ids = {r['id'] for r in excluded}
opened, evidence = fresh.historical_exposure([root, fresh.MAIN, fresh.EARLIER], a.dataset.name)
assert opened <= excluded_ids
assert not selected_ids & excluded_ids
assert len(selected_ids) == len(selected) == 2000
for split, count in [('development',500),('validation',1000),('test',500)]:
    assert sum(r['split']==split for r in selected) == count
# The preparer and audit compare normalized content, not only identifiers.
spec = importlib.util.spec_from_file_location('prepare', root/'datasets/scripts/prepare_data.py')
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)
_, excluded_hashes, _ = prepare.exclusion_manifest([a.dataset.with_name(a.dataset.name+'-prior-opened')])
hashes = []
for row in selected:
    payload = json.loads((a.dataset/row['input']).read_text())
    hashes.append(hashlib.sha256(prepare.normalized_case_content(payload).encode()).hexdigest())
assert len(set(hashes)) == 2000
assert not set(hashes) & excluded_hashes
result = {'passed': True, 'dataset': a.dataset.name, 'selected_cases': 2000,
          'excluded_cases': len(excluded_ids), 'historically_executed_cases': len(opened),
          'historical_evidence_files': len(evidence), 'prior_id_overlap': 0,
          'prior_normalized_content_overlap': 0, 'unique_normalized_contents': 2000,
          'evals_sha256': hashlib.sha256((a.dataset/'evals.csv').read_bytes()).hexdigest()}
assert not a.output.exists()
a.output.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
