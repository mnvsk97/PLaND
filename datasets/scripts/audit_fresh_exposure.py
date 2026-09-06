#!/usr/bin/env python3
"""Read-only corpus audit; write a freshness incident and capacity receipt."""
import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from prepare_fresh_collection import ROOT, MAIN, EARLIER, historical_exposure, sha
from prepare_data import deduplicate_text


def content_hash(text):
    return hashlib.sha256(' '.join(text.split()).casefold().encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Preserve existing audit; choose a new output')
    base = ROOT/'tmp/fresh-paper-20260905'
    source = MAIN/'tmp/enterprise-datasets/ledgar/sources'
    records, sources = [], []
    lock = json.loads((ROOT/'datasets/sources.lock.json').read_text())
    for part in ['train','validation','test']:
        path = source/f'{part}.jsonl'
        expected = next(v for v in lock['sources']['ledgar']['files'] if Path(v['path']).name == path.name)
        assert sha(path) == expected['sha256'] and path.stat().st_size == expected['bytes']
        sources.append({'path':str(path),'sha256':sha(path),'bytes':path.stat().st_size})
        with path.open() as handle:
            for number, line in enumerate(handle, 1):
                value = json.loads(line)
                if len(value.get('gold',[])) == 1 and value.get('input','').strip():
                    records.append({'id':f'{part}-{number}','text':value['input'],
                                    'label':value['gold'][0],'partition':part})
    lookup = {r['id']:r for r in records}
    records = deduplicate_text(records, 'text', 'id')
    opened, evidence = historical_exposure([ROOT,MAIN,EARLIER], 'ledgar')
    for directory, splits in [
        (MAIN/'tmp/confirmatory-datasets/ledgar',{'development','validation','test'}),
        (EARLIER/'tmp/quality-first-datasets/ledgar',{'development','validation'})]:
        path = directory/'evals.csv'
        with path.open() as handle:
            ids = {r['id'] for r in csv.DictReader(handle) if r['split'] in splits}
        opened.update(ids)
        evidence.append({'path':str(path),'sha256':sha(path),'cases':len(ids),'included_splits':sorted(splits)})
    missing = opened-set(lookup)
    assert not missing, sorted(missing)
    hashes = {content_hash(lookup[i]['text']) for i in opened}
    with (base/'datasets/ledgar/evals.csv').open() as handle:
        current = list(csv.DictReader(handle))
    pilot_path = ROOT/'experiments/ledgar-text-classification/paper-subset.json'
    pilot = {c['id'] for c in json.loads(pilot_path.read_text())['selected']}
    overlaps = [{'id':r['id'],'current_split':r['split']} for r in current if r['id'] in pilot]
    reserved = {r['id'] for r in current if r['split']=='test'}
    # In-flight requests may not have reached the last checkpoint. Quarantine the
    # entire interrupted final reservation instead of claiming unrecorded cases unused.
    quarantined_hashes = hashes | {content_hash(lookup[i]['text']) for i in reserved}
    labels = json.loads((base/'datasets/ledgar/selection.json').read_text())['labels']
    capacity = {}
    for label in labels:
        capacity[label] = {}
        for partition in ['train','validation','test']:
            pool = [r for r in records if r['label']==label and r['partition']==partition]
            untouched = [r for r in pool if r['id'] not in opened and content_hash(r['text']) not in hashes]
            quarantined = [r for r in untouched if r['id'] not in reserved and content_hash(r['text']) not in quarantined_hashes]
            capacity[label][partition] = {'source_unique':len(pool), 'not_in_recorded_exposure':len(untouched),
                                          'available_after_quarantine':len(quarantined)}
    required = {'train':50,'validation':100,'test':50}
    deficits = [{'label':label,'partition':part,'required':n,
                 'available':capacity[label][part]['available_after_quarantine']}
                for label in labels for part,n in required.items()
                if capacity[label][part]['available_after_quarantine'] < n]
    checkpoint = base/'runs/ledgar/test-20260902-baseline.json.partial.json'
    checkpoint_cases = len(json.loads(checkpoint.read_text())['cases'])
    result = {
        'status':'INVALID_FRESHNESS', 'created_at':datetime.now(UTC).isoformat(),
        'reason':'Aggregate-only earliest paper pilot omitted from original exclusion collection.',
        'source_custody':sources, 'historical_evidence':evidence,
        'confirmed_pilot_overlap':overlaps, 'overlap_counts':dict(Counter(x['current_split'] for x in overlaps)),
        'completed_final_checkpoint_cases':checkpoint_cases, 'final_reservation_quarantined':len(reserved),
        'exposure_ledger':[{'id':i,'normalized_content_sha256':content_hash(lookup[i]['text'])} for i in sorted(opened)],
        'quarantined_final_ids':sorted(reserved), 'capacity':capacity,
        'required_per_label_by_official_partition':required, 'deficits':deficits,
        'approved_plan_restart_feasible':not deficits,
        'all_partition_pooled_capacity_sufficient':all(sum(v['available_after_quarantine'] for v in capacity[label].values()) >= 200 for label in labels),
        'pooled_sampling_authorized':False,
        'approval_needed':'Pooling official partitions would amend the approved LEDGAR source-boundary rule; do not do it silently.',
        'run_disposition':'All current LEDGAR outputs invalid as fresh paper evidence; preserve and do not resume.',
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['status','overlap_counts','completed_final_checkpoint_cases','deficits','all_partition_pooled_capacity_sufficient']}))


if __name__ == '__main__':
    main()
