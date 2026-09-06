"""Check new IDs/content directly against the separately recovered incident ledger."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
root=Path.cwd();base=root/'tmp/fresh-paper-ledgar-training-20260905'
incident_path=root/'experiments/fresh-paper-20260905/ledgar-freshness-incident.json'
incident=json.loads(incident_path.read_text())
previous_ids={r['id'] for r in incident['exposure_ledger']}|set(incident['quarantined_final_ids'])
previous_hashes={r['normalized_content_sha256'] for r in incident['exposure_ledger']}
with (base/'datasets/ledgar/evals.csv').open() as h: rows=list(csv.DictReader(h))
with (base/'datasets/ledgar-prior-opened/evals.csv').open() as h: exclusions=list(csv.DictReader(h))
assert previous_ids <= {r['id'] for r in exclusions}, 'Recovered history missing from exclusions'
assert len(rows)==2000 and all(r['id'].startswith('train-') for r in rows)
selected=json.loads((base/'datasets/ledgar/selection.json').read_text())
assert selected['source_split_mapping']==dict.fromkeys(['development','validation','test'],'train')
ids={r['id'] for r in rows};hashes=set()
for row in rows:
    payload=json.loads((base/'datasets/ledgar'/row['input']).read_text())
    hashes.add(hashlib.sha256(' '.join(payload['text'].split()).casefold().encode()).hexdigest())
assert not ids & previous_ids and not hashes & previous_hashes
assert len(ids)==len(hashes)==2000
result={'passed':True,'new_cases':2000,'all_official_training_rows':True,
        'recovered_prior_ids':len(previous_ids),'prior_exclusion_ids':len(exclusions),
        'id_overlap':0,'normalized_content_overlap':0,'all_recovered_prior_ids_excluded':True,
        'incident_sha256':hashlib.sha256(incident_path.read_bytes()).hexdigest()}
assert not a.output.exists()
a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
